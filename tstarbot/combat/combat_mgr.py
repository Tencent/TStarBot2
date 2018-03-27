"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import math
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp


class BaseCombatMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass


class BasicCombatMgr(BaseCombatMgr):
    """ Basic Combat Manager

    Common Utilites for combat are implemented here. """

    def __init__(self):
        super(BasicCombatMgr, self).__init__()

    def update(self, dc, am):
        super(BasicCombatMgr, self).update(dc, am)

    def attack_closest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_closest_enemy(u, enemies=enemies)

        action.action_raw.unit_command.target_unit_tag = u.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_weakest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_weakest_enemy(enemies=enemies)

        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def run_away_from_closest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.SMART.value
        target = self.find_closest_enemy(u, enemies=enemies)

        action.action_raw.unit_command.target_world_space_pos.x = u.float_attr.pos_x + \
            (u.float_attr.pos_x - target.float_attr.pos_x) * 0.2
        action.action_raw.unit_command.target_world_space_pos.y = u.float_attr.pos_y + \
            (u.float_attr.pos_y - target.float_attr.pos_y) * 0.2
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def find_closest_enemy(self, u, enemies):
        dist = []
        for e in enemies:
            dist.append(self.cal_square_dist(u, e))
        idx = np.argmin(dist)
        return enemies[idx]

    @staticmethod
    def find_weakest_enemy(enemies):
        hp = []
        for e in enemies:
            hp.append(e.float_attr.health)
        idx = np.argmin(hp)
        if hp[idx] == np.max(hp):
            idx = 0
        return enemies[idx]

    @staticmethod
    def find_strongest_unit_hp(units):
        hp = []
        for m in units:
            hp = m.float_attr.health / m.float_attr.health_max
        max_hp = np.max(hp)
        return max_hp

    @staticmethod
    def cal_square_dist(u1, u2):
        return pow(u1.float_attr.pos_x - u2.float_attr.pos_x, 2) + pow(u1.float_attr.pos_y - u2.float_attr.pos_y, 2)


class ZergCombatLxHanMgr(BaseCombatMgr):
    """ Combat module for full game """
    def __init__(self):
        super(ZergCombatLxHanMgr, self).__init__()
        self.enemy_pos_cnt_max = 0

    def reset(self):
        self.enemy_pos_cnt_max = 0

    def update(self, dc, am):
        super(ZergCombatLxHanMgr, self).update(dc, am)

        roaches = dc.get_roaches()
        hydralisk = dc.get_hydralisk()
        base_pos = dc.base_pos
        minimap = dc.mini_map

        actions = list()
        pos = self.find_enemy_base_pos(base_pos, minimap)
        squad = roaches + hydralisk
        actions.extend(self.attack_pos(squad, pos, 15))

        am.push_actions(actions)

    @staticmethod
    def attack_pos(units, pos, n):
        actions = []
        if len(units) >= n:
            for u in units:
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = tp.ABILITY_ID.ATTACK_ATTACK.value
                action.action_raw.unit_command.target_world_space_pos.x = pos[0]
                action.action_raw.unit_command.target_world_space_pos.y = pos[1]
                action.action_raw.unit_command.unit_tags.append(u.tag)
                actions.append(action)

        return actions

    def find_enemy_base_pos(self, base_pos, minimap):
        if len(base_pos) == 0:
            return [0, 0]

        # [57.5, 27.5] -> mini map 1-dim [40:50] 2-dim [40:50]
        minimap_pos1 = minimap[5][15:35][10:30]
        minimap_pos2 = minimap[5][10:30][35:55]
        minimap_pos3 = minimap[5][40:60][5:25]
        minimap_pos4 = minimap[5][40:60][35:55]

        pos_1 = [base_pos[1], base_pos[0]]

        # np.set_printoptions(threshold=10000)
        # print(minimap[5])
        if base_pos[0] > base_pos[1]:
            pos_2 = [59.5, 59.5]

            pos_1_enemy_cnt = np.reshape(minimap_pos1, [1, -1])[0].tolist().count(4)
            print('pos1', pos_1_enemy_cnt)
            if pos_1_enemy_cnt > self.enemy_pos_cnt_max:
                self.enemy_pos_cnt_max = pos_1_enemy_cnt
            if pos_1_enemy_cnt < 2 and self.enemy_pos_cnt_max > 5:
                return pos_2
        else:
            pos_2 = [27.5, 27.5]

            pos_3_enemy_cnt = np.reshape(minimap_pos3, [1, -1])[0].tolist().count(4)
            print('pos3', pos_3_enemy_cnt)
            if pos_3_enemy_cnt > self.enemy_pos_cnt_max:
                self.enemy_pos_cnt_max = pos_3_enemy_cnt
            if pos_3_enemy_cnt < 2 and self.enemy_pos_cnt_max > 5:
                return pos_2

        return pos_1


class ZergCombatMgr(BasicCombatMgr):
    """ A zvz Zerg combat manager """

    def __init__(self):
        super(ZergCombatMgr, self).__init__()

    def update(self, dc, am):
        super(ZergCombatMgr, self).update(dc, am)

        actions = list()

        # TODO: impl

        am.push_actions(actions)

