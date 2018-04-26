import os
import portpicker
import sys
import absl
import time

from pysc2 import maps
from pysc2 import run_configs
from pysc2.env import environment
from pysc2.lib import features
from pysc2.lib import point
from pysc2.lib import run_parallel
from pysc2.tests import utils

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

from tstarbot.agents.dancing_drones_agent import DancingDronesAgent
from tstarbot.agents.zerg_agent import ZergAgent
from pysc2.lib import unit_controls
from collections import namedtuple


def test_multi_player():
    players = 2
    agent1 = ZergAgent()
    agent2 = ZergAgent()
    run_config = run_configs.get()
    parallel = run_parallel.RunParallel()
    map_inst = maps.get("AbyssalReef")

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
      join = sc_pb.RequestJoinGame(race=sc_common.Zerg, options=interface)
      join.shared_port = ports.pop()
      join.server_ports.game_port = ports.pop()
      join.server_ports.base_port = ports.pop()
      for _ in range(players - 1):
        join.client_ports.add(game_port=ports.pop(), base_port=ports.pop())

      # This is where actually game plays
      # Create and Join
      print("create")
      controllers[0].create_game(create)
      print("join")
      parallel.run((c.join_game, join) for c in controllers)

      print("run")
      game_info = controllers[0].game_info()
      extractors = features.Features(game_info)
      for game_loop in range(1, 100000):  # steps per episode
        # Step the game
        step_mul = 8
        if not real_time:
          parallel.run((c.step, step_mul) for c in controllers)
        else:
          time.sleep(0.2)

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
        #actions1 = agent1.step(timesteps[0])
        actions2 = agent2.step(timesteps[1])
        actions = [[], actions2]
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

if __name__ == "__main__":
    FLAGS = absl.flags.FLAGS
    FLAGS(sys.argv)
    test_multi_player()
