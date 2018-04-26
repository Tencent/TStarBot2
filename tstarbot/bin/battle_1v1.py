from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib import point
from pysc2.lib import renderer_human
from pysc2.lib import unit_controls
from pysc2.lib import run_parallel
from pysc2.lib import features
from pysc2.env import environment
from pysc2 import maps
from pysc2 import run_configs
from pysc2.env.sc2_env import races, difficulties
from pysc2.lib.remote_controller import RequestError

from s2clientprotocol import common_pb2 as sc_common
from s2clientprotocol import sc2api_pb2 as sc_pb

from tstarbot.agents.dancing_drones_agent import DancingDronesAgent
from tstarbot.agents.zerg_agent import ZergAgent
from collections import namedtuple

import os
import time
import threading
import portpicker
import importlib
import copy
import traceback

from absl import logging
from absl import app
from absl import flags

FLAGS = flags.FLAGS
flags.DEFINE_bool("render", True, "Whether to render with pygame.")
flags.DEFINE_integer("screen_resolution", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("minimap_resolution", 64,
                     "Resolution for minimap feature layers.")

flags.DEFINE_integer("max_step", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_string("player1_agent", "pysc2.agents.random_agent.RandomAgent", "Which agent to run")
flags.DEFINE_string("player2_agent", "pysc2.agents.random_agent.RandomAgent", "Which agent to run")
flags.DEFINE_string("player1_agent_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_string("player2_agent_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_string("player1_race", 'Z', "player1's race.")
flags.DEFINE_string("player2_race", 'Z', "player2's race.")
flags.DEFINE_bool("disable_fog", False, "Turn off the Fog of War.")
flags.DEFINE_string("save_replay", None, "Whether to save a replay at the end.")
flags.DEFINE_string("map", None, "Name of a map to use.")
flags.mark_flag_as_required("map")
flags.mark_flag_as_required("save_replay")
flags.mark_flag_as_required("player1_agent")
flags.mark_flag_as_required("player2_agent")


GAME_NUM_1V1 = 2
DEF_MAX_STEP = 5000

races = {
    'R': sc_common.Random,
    'P': sc_common.Protoss,
    'T': sc_common.Terran,
    'Z': sc_common.Zerg,
}

class Battle1V1:
    def __init__(self,
                 map_name=None,
                 agent_races=('Z', 'Z'),
                 screen_resolution=(64, 64),
                 minimap_resolution=(64, 64),
                 visualize=True,
                 disable_fog=False,
                 save_replay=None,
                 max_step=None,
                 **kwargs):
        self._envs = None
        self._agents = None

        self._map_name = map_name
        self._races = [races[agent_races[0]], races[agent_races[1]]]
        self._screen = point.Point(screen_resolution[0], screen_resolution[1])
        self._minimap = point.Point(minimap_resolution[0], minimap_resolution[1])
        self._visualize = visualize
        self._save_replay = save_replay
        if max_step is None:
            self._max_step = DEF_MAX_STEP
        elif max_step == 0 or max_step > DEF_MAX_STEP:
            self._max_step = DEF_MAX_STEP
        else:
            self._max_step = max_step

        self._kwargs = kwargs
        self._controllers = None

    def setup(self):
        try:
            self._get_ports()
            self._load_maps()
            self._launch_gamecores()
            self._setup_game()
        except Exception:
            print('catch exception while setup')
            traceback.print_exc()
            print('RESULT player{} {}'.format(1, 4))
            print('RESULT player{} {}'.format(2, 4))
            return False
        else:
            return True

    def play(self):
        results = None
        try:
            results = self._play()
        except:
            print('catch exception while play')
            traceback.print_exc()
            if results is None or 0 == len(results):
                print('RESULT player{} {}'.format(1, 4))
                print('RESULT player{} {}'.format(2, 4))
        else:
            if results is None or 0 == len(results):
                print('RESULT player{} {}'.format(1, 4))
                print('RESULT player{} {}'.format(2, 4))
            else:
                for result in results:
                    print('RESULT player{} {}'.format(result.player_id, result.result))
            self._save_game()
            self._leave_game()
            self._exit_game()

    def register_agent(self, agents):
        if len(agents) != GAME_NUM_1V1:
            raise Exception('the number of input agents invalid')
        self._agents = agents 

    def _load_maps(self):
        self._map = maps.get(self._map_name)
        print("MapInfo: [player_num={}, path_name={}]".format(
              self._map.players, self._map.filename))
        if self._map.players < len(self._agents):
            raise Exception("the player number of map is err")

    def _launch_gamecores(self):
        num = len(self._agents)
        self._run_config = run_configs.get()
        self._sc2_procs = [self._run_config.start(extra_ports=self._ports)
                           for _ in range(num)]
        self._controllers = [p.controller for p in self._sc2_procs]
        self._parallel = run_parallel.RunParallel()

    def _get_ports(self):
        self._ports = [portpicker.pick_unused_port() 
                       for _ in range(1 + len(self._agents) * 2)]

    def _return_ports(self):
        for port in self._ports:
            portpicker.return_port(port)

    def _join_pb(self, agent_race, interface):
        ports = copy.deepcopy(self._ports)
        join = sc_pb.RequestJoinGame(race=agent_race, options=interface)
        join.shared_port = ports.pop()
        join.server_ports.game_port = ports.pop()
        join.server_ports.base_port = ports.pop()
        for _ in range(len(self._agents) - 1):
            join.client_ports.add(game_port=ports.pop(), base_port=ports.pop())
        return join

    def _setup_game(self):
        # Save the maps so they can access it.
        map_path = os.path.basename(self._map.path)
        self._parallel.run((c.save_map, map_path, 
                            self._run_config.map_data(self._map.path))
                           for c in self._controllers)

        # construct interface
        interface = sc_pb.InterfaceOptions(raw=True, score=True)
        self._screen.assign_to(interface.feature_layer.resolution)
        self._minimap.assign_to(interface.feature_layer.minimap_resolution)

        # Create the create request.
        create = sc_pb.RequestCreateGame(local_map=sc_pb.LocalMap(map_path=map_path))
        for _ in range(len(self._agents)):
            create.player_setup.add(type=sc_pb.Participant)

        # Create the join request.
        joins = [ self._join_pb(race, interface) for race in self._races ]

        # This is where actually game plays
        # Create and Join
        print("create")
        self._controllers[0].create_game(create)
        print("join")
        self._parallel.run((c.join_game, join) for join, c in zip(joins, self._controllers))
        print("play_game")
        self._game_infos = self._parallel.run((c.game_info) for c in self._controllers)
        self._features = [ features.Features(info) for info in self._game_infos ]
        print("setup game ok")
        #print('game_info len=', len(self._game_infos))
        #print('features len=', len(self._features))

    def _play(self):
        run = True
        step_counter = 0
        results = []
        while(True):
            #print('run loop=', step_counter)
            # Step the game
            self._parallel.run(c.step for c in self._controllers)

            # Observe
            obs = self._parallel.run(c.observe for c in self._controllers)
            agent_obs = [f.transform_obs(o.observation) for f, o in zip(self._features, obs)]

            if step_counter == 0:
                stype = environment.StepType.FIRST
            elif any(o.player_result for o in obs):
                for o in obs:
                    results.append(o.play_result)
                stype = environment.StepType.LAST
            else:
                stype = environment.StepType.MID

            timesteps = tuple(environment.TimeStep(step_type=stype,
                                                   reward=0, discount=0, observation=o,
                                                   game_info=i)
                              for o,i in zip(agent_obs, self._game_infos))
            # Act
            actions1 = self._agents[0].step(timesteps[0])
            actions2 = self._agents[1].step(timesteps[1])
            actions = [actions1, actions2]
            #actions = [[], []]
            #print(actions)
            self._parallel.run((c.acts, a) for c, a in zip(self._controllers, actions))
            step_counter += 1
            if step_counter >= self._max_step:
                break
            if stype == environment.StepType.LAST:
                break
            # Done with the game.
        return results

    def _leave_game(self):
        if self._controllers is None:
            return

        for c in self._controllers:
            c.leave()

    def _exit_game(self):
        if self._controllers is None:
            return

        for c in self._controllers:
            c.quit()
        self._controllers = None
        self._return_ports()

    def _save_game(self):
        path = self._run_config.save_replay(self._controllers[0].save_replay(), 
                                     self._save_replay, 
                                     self._map.name)
        print('save_replay path=', path)

def zerg_test():
    game = Battle1V1(map_name='Simple64')
    agent1 = ZergAgent()
    agent2 = ZergAgent()
    game.register_agent([agent1, agent2])
    if game.setup():
        game.play()

def load_agent(path, config):
    agent_module, agent_name = path.rsplit(".", 1)
    agent_cls = getattr(importlib.import_module(agent_module), agent_name)
    agent_kwargs = {}
    if config:
        agent_kwargs['config_path'] = config
    return agent_cls(**agent_kwargs)

def main_func():
    agent1 = load_agent(FLAGS.player1_agent, FLAGS.player1_agent_config)
    agent2 = load_agent(FLAGS.player2_agent, FLAGS.player2_agent_config)

    agents=[agent1, agent2]
    races=(FLAGS.player1_race, FLAGS.player2_race)

    game = Battle1V1(map_name=FLAGS.map,
              agent_races=races,
              save_replay=FLAGS.save_replay,
              visualize=True,
              disable_fog=FLAGS.disable_fog,
              max_step=FLAGS.max_step)
    game.register_agent(agents)
    if game.setup():
        game.play()

def main(unused_argv):
    main_func()

def entry_point():  # Needed so setup.py scripts work.
    app.run(main)

if __name__ == "__main__":
    app.run(main)

