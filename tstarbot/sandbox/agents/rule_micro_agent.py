""" lxhan
A rule based multi-agent micro-management bot. seems working well that sometimes can reach grandmaster human player's performance.
Run bin/eval_micro.py to see the game.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import math
import numpy as np
from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.sandbox.bot_base import PoolBase, ManagerBase
from tstarbot.sandbox.act_executor import ActExecutor


UNIT_TYPE_MARINE = 48
UNIT_TYPE_ROACH = 110

MOVE = 1
ATTACK = 23
ATTACK_TOWARDS = 24

ROACH_ATTACK_RANGE = 5.0


# A pool containing all units that you want to operate
class UnitPool(PoolBase):
    def __init__(self):
        self.marines = []
        self.roaches = []

    def update(self, obs):
        units = obs['units']
        # print(units)
        self.collect_marine(units)
        self.collect_roach(units)

    def collect_marine(self, units):
        marines = []
        for u in units:
            if u.unit_type == UNIT_TYPE_MARINE and u.int_attr.owner == 1:
                marines.append(u)
                # print("marine assigned_harvesters: {}".format(u.int_attr.assigned_harvesters))
        self.marines = marines

    def collect_roach(self, units):
        roaches = []
        for u in units:
            if u.unit_type == UNIT_TYPE_ROACH and u.int_attr.owner == 2:
                roaches.append(u)
                # print("roach target: {}".format(u.int_attr.engaged_target_tag))
        self.roaches = roaches

    def get_marines(self):
        return self.marines

    def get_roaches(self):
        return self.roaches


class MicroManager(ManagerBase):
    def __init__(self, pool):
        self._pool = pool
        self._range_high = 5
        self._range_low = -5
        self.marines = None
        self.roaches = None

    def execute(self):
        self.marines = self._pool.get_marines()
        self.roaches = self._pool.get_roaches()
        actions = self.operate()
        return actions

    def operate(self):
        actions = list()
        for m in self.marines:
            closest_enemy_dist = math.sqrt(self.cal_square_dist(m, self.find_closest_enemy(m, self.roaches)))
            if closest_enemy_dist < ROACH_ATTACK_RANGE and (m.float_attr.health / m.float_attr.health_max) < 0.3 and self.find_strongest_unit() > 0.9:
                action = self.run_away_from_closest_enemy(m)
            else:
                action = self.attack_weakest_enemy(m)
            actions.append(action)
        return actions

    def attack_closest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ATTACK
        target = self.find_closest_enemy(u, enemies=self.roaches)

        action.action_raw.unit_command.target_unit_tag = u.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_weakest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ATTACK
        target = self.find_weakest_enemy(enemies=self.roaches)

        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def run_away_from_closest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = MOVE
        target = self.find_closest_enemy(u, enemies=self.roaches)

        action.action_raw.unit_command.target_world_space_pos.x = u.float_attr.pos_x + (u.float_attr.pos_x - target.float_attr.pos_x) * 0.2
        action.action_raw.unit_command.target_world_space_pos.y = u.float_attr.pos_y + (u.float_attr.pos_y - target.float_attr.pos_y) * 0.2
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def find_closest_enemy(self, u, enemies):
        dist = []
        for e in enemies:
            dist.append(self.cal_square_dist(u, e))
        idx = np.argmin(dist)
        # print('closest dist: {}'.format(math.sqrt(dist[idx])))
        return enemies[idx]

    def find_weakest_enemy(self, enemies):
        hp = []
        for e in enemies:
            hp.append(e.float_attr.health)
        idx = np.argmin(hp)
        if hp[idx] == np.max(hp):
            idx = 0
        return enemies[idx]

    def find_strongest_unit(self):
        hp = []
        for m in self.marines:
            hp = m.float_attr.health / m.float_attr.health_max
        max_hp = np.max(hp)
        return max_hp

    @staticmethod
    def cal_square_dist(u1, u2):
        return pow(u1.float_attr.pos_x - u2.float_attr.pos_x, 2) + pow(u1.float_attr.pos_y - u2.float_attr.pos_y, 2)


class MicroAgent:
    """A random agent for starcraft."""
    def __init__(self, env):
        self._pools = []
        self._managers = []
        self._env = env
        self._executor = []

    def setup(self):
        pool = UnitPool()
        task_manager = MicroManager(pool)
        self._pools.append(pool)
        self._managers.append(task_manager)
        self._executor = ActExecutor(self._env)

    def reset(self):
        timesteps = self._env.reset()
        return timesteps

    def run(self, n):
        return self._run_inner(n)

    def _run_inner(self, n):
        try:
            """episode loop """
            step_num = 0
            timesteps = self.reset()
            while True:
                obs = timesteps[0].observation
                for pool in self._pools:
                    pool.update(obs)

                actions = []
                for manager in self._managers:
                    part_actions = manager.execute()
                    actions.extend(part_actions)

                result = self._executor.exec_raw(actions)
                if result[1]:
                    timesteps = self.reset()
                    continue
                    # break
                timesteps = result[0]

                if step_num > n:
                    break
                step_num += 1
        except KeyboardInterrupt:
            print("SC2Imp exception")
