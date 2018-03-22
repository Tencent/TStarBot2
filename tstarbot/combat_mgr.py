"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import math
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp

ROACH_ATTACK_RANGE = 5.0


class BaseCombatMgr(object):
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass


class DefeatRoachesCombatMgr(BaseCombatMgr):
    """ Combat Manager for the DefeatRoaches minimap"""

    def __init__(self):
        super(DefeatRoachesCombatMgr, self).__init__()
        self.marines = None
        self.roaches = None

    def update(self, obs_mgr, act_mgr):
        super(DefeatRoachesCombatMgr, self).update(obs_mgr, act_mgr)
        self.marines = obs_mgr.marines
        self.roaches = obs_mgr.roaches

        actions = list()
        for m in self.marines:
            closest_enemy_dist = math.sqrt(self.cal_square_dist(m, self.find_closest_enemy(m, self.roaches)))
            if closest_enemy_dist < ROACH_ATTACK_RANGE and (
                m.float_attr.health / m.float_attr.health_max) < 0.3 and self.find_strongest_unit() > 0.9:
                action = self.run_away_from_closest_enemy(m)
            else:
                action = self.attack_weakest_enemy(m)
            actions.append(action)

        act_mgr.push_actions(actions)

    def attack_closest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_closest_enemy(u, enemies=self.roaches)

        action.action_raw.unit_command.target_unit_tag = u.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_weakest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_weakest_enemy(enemies=self.roaches)

        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def run_away_from_closest_enemy(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.SMART.value
        target = self.find_closest_enemy(u, enemies=self.roaches)

        action.action_raw.unit_command.target_world_space_pos.x = u.float_attr.pos_x + (
                u.float_attr.pos_x - target.float_attr.pos_x) * 0.2
        action.action_raw.unit_command.target_world_space_pos.y = u.float_attr.pos_y + (
                u.float_attr.pos_y - target.float_attr.pos_y) * 0.2
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


class ZergCombatMgr(BaseCombatMgr):
    """ A zvz Zerg combat manager """

    def __init__(self):
        super(ZergCombatMgr, self).__init__()

    def update(self, dc, am):
        super(ZergCombatMgr, self).update(dc, am)

        actions = []

        # TODO: impl

        am.push_actions(actions)
