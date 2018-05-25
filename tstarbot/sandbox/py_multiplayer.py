import os
import portpicker
import sys
import time
import importlib

from pysc2 import maps
from pysc2.env import sc2_env
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import run_parallel
from pysc2.tests import utils
import copy

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import debug_pb2

from tstarbot.agents.zerg_agent import ZergAgent

from absl import flags
from absl import app

races = {
    "R": sc_common.Random,
    "P": sc_common.Protoss,
    "T": sc_common.Terran,
    "Z": sc_common.Zerg,
}

FLAGS = flags.FLAGS
flags.DEFINE_bool("realtime", True, "Whether to run in real time.")

flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")
flags.DEFINE_float("sleep_time", 0.2, "Sleep time between agent steps.")

flags.DEFINE_string("agent1", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run")
flags.DEFINE_string("agent1_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_string("agent2", None,
                    "Which agent to run")
flags.DEFINE_string("agent2_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_enum("agent1_race", None, sc2_env.races.keys(), "Agent1's race.")
flags.DEFINE_enum("agent2_race", None, sc2_env.races.keys(), "Agent2's race.")

flags.DEFINE_bool("disable_fog_1", False, "Turn off the Fog of War for agent 1.")
flags.DEFINE_bool("disable_fog_2", False, "Turn off the Fog of War for agent 2.")

flags.DEFINE_string("map", None, "Name of a map to use.")
flags.mark_flag_as_required("map")


def test_multi_player(agents, disable_fog):
    players = 2
    if len(agents) == 2:
        agent1, agent2 = agents
    run_config = run_configs.get()
    parallel = run_parallel.RunParallel()
    map_inst = maps.get(FLAGS.map)

    screen_size_px = point.Point(64, 64)
    minimap_size_px = point.Point(32, 32)
    interface = sc_pb.InterfaceOptions(
        raw=True, score=True)
    screen_size_px.assign_to(interface.feature_layer.resolution)
    minimap_size_px.assign_to(interface.feature_layer.minimap_resolution)

    # Reserve a whole bunch of ports for the weird multiplayer implementation.
    ports = [portpicker.pick_unused_port() for _ in range(1 + players * 2)]
    print("Valid Ports: %s", ports)

    # Actually launch the game processes.
    print("start")
    sc2_procs = [run_config.start(extra_ports=ports) for _ in range(players)]
    controllers = [p.controller for p in sc2_procs]

    try:
        # Save the maps so they can access it.
        map_path = os.path.basename(map_inst.path)
        print("save_map")
        parallel.run((c.save_map, map_path, run_config.map_data(map_inst.path))
                     for c in controllers)

        # Create the create request.
        real_time = True
        create = sc_pb.RequestCreateGame(
            local_map=sc_pb.LocalMap(map_path=map_path), realtime=real_time)
        for _ in range(players):
            create.player_setup.add(type=sc_pb.Participant)

        # Create the join request.
        join1 = sc_pb.RequestJoinGame(race=races[FLAGS.agent1_race], options=interface)
        join1.shared_port = ports.pop()
        join1.server_ports.game_port = ports.pop()
        join1.server_ports.base_port = ports.pop()
        join1.client_ports.add(game_port=ports.pop(), base_port=ports.pop())

        join2 = copy.copy(join1)
        join2.race = races[FLAGS.agent2_race]

        # This is where actually game plays
        # Create and Join
        print("create")
        controllers[0].create_game(create)
        print("join")
        parallel.run((c.join_game, join) for c, join in zip(controllers, [join1, join2]))

        controllers[0]._client.send(debug=sc_pb.RequestDebug(
                    debug=[debug_pb2.DebugCommand(game_state=1)]))
        if disable_fog[0]:
            controllers[0].disable_fog()
        if disable_fog[1]:
            controllers[1].disable_fog()

        print("run")
        game_info = controllers[0].game_info()
        extractors = features.Features(game_info)
        for game_loop in range(1, 100000):  # steps per episode
            # Step the game
            step_mul = FLAGS.step_mul
            if not real_time:
                parallel.run((c.step, step_mul) for c in controllers)
            else:
                time.sleep(FLAGS.sleep_time)

            # Observe
            obs = parallel.run(c.observe for c in controllers)
            agent_obs = [extractors.transform_obs(o.observation) for o in obs]
            game_info = [None for c in controllers]

            if not any(o.player_result for o in obs):  # Episode over.
                game_info = parallel.run(c.game_info for c in controllers)
            timesteps = tuple(environment.TimeStep(step_type=0,
                                                   reward=0,
                                                   discount=0, observation=o,
                                                   game_info=info)
                              for o, info in zip(agent_obs, game_info))

            # Act
            if agent1 is not None:
                actions1 = agent1.step(timesteps[0])
            else:
                actions1 = []
            actions2 = agent2.step(timesteps[1])
            actions = [actions1, actions2]
            funcs_with_args = [(c.acts, a) for c, a in zip(controllers, actions)]
            parallel.run(funcs_with_args)

        # Done with the game.
        print("leave")
        parallel.run(c.leave for c in controllers)
    finally:
        print("quit")
        # Done, shut down. Don't depend on parallel since it might be broken.
        for c in controllers:
            c.quit()
        for p in sc2_procs:
            p.close()


def main(unused_argv):
    """Run an agent."""
    maps.get(FLAGS.map)  # Assert the map exists.

    agent_module, agent_name = FLAGS.agent1.rsplit(".", 1)
    agent_cls = getattr(importlib.import_module(agent_module), agent_name)
    agent1_kwargs = {}
    if FLAGS.agent1_config:
        agent1_kwargs['config_path'] = FLAGS.agent1_config
    agent1 = agent_cls(**agent1_kwargs)

    if FLAGS.agent2:
        agent_module, agent_name = FLAGS.agent2.rsplit(".", 1)
        agent_cls = getattr(importlib.import_module(agent_module), agent_name)
        agent2_kwargs = {}
        if FLAGS.agent1_config:
            agent2_kwargs['config_path'] = FLAGS.agent2_config
        agent2 = agent_cls(**agent2_kwargs)
        test_multi_player([agent2, agent1], [FLAGS.disable_fog_2, FLAGS.disable_fog_1])
    else:
        test_multi_player([None, agent1], [FLAGS.disable_fog_2, FLAGS.disable_fog_1])


if __name__ == "__main__":
    app.run(main)
