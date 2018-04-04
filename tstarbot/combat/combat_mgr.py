"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import math
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID


ATTACK_MODE = 0
RETREAT_MODE = 1
DEFEND_MODE = 2


def collect_units(units, unit_type, owner=1):
    return [u for u in units
            if u.unit_type == unit_type and u.int_attr.owner == owner]


class BaseCombatMgr(object):
    """ Basic Combat Manager

    Common Utilites for combat are implemented here. """

    def __init__(self):
        pass

    def reset(self):
        pass

    def update(self, dc, am):
        pass

    @staticmethod
    def attack_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        action.action_raw.unit_command.target_world_space_pos.x = pos[0]
        action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_closest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_closest_enemy(u, enemies=enemies)
        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_weakest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_weakest_enemy(enemies=enemies)
        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def run_away_from_closest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.SMART.value
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
        return pow(u1.float_attr.pos_x - u2.float_attr.pos_x, 2) + \
               pow(u1.float_attr.pos_y - u2.float_attr.pos_y, 2)


class ZergCombatLxHanMgr(BaseCombatMgr):
    """ Combat module for full game """
    def __init__(self):
        super(ZergCombatLxHanMgr, self).__init__()
        self.enemy_pos_cnt_max = 0
        self.roach_attack_range = 5.0
        self.enemy_units = []

    def reset(self):
        self.enemy_pos_cnt_max = 0
        self.enemy_units = []

    def update(self, dc, am):
        super(ZergCombatLxHanMgr, self).update(dc, am)

        roaches = dc.get_roaches()
        hydralisk = dc.get_hydralisk()
        base_pos = dc.base_pos
        minimap = dc.mini_map
        self.enemy_units = dc.get_enemy_units()

        actions = list()
        pos = self.find_enemy_base_pos(base_pos, minimap)
        squad = roaches + hydralisk
        if len(squad) >= 15:
            actions.extend(self.exe_cmd(squad, pos, ATTACK_MODE))

        am.push_actions(actions)

    def exe_cmd(self, squad, pos, mode):
        actions = []
        if mode == ATTACK_MODE:
            actions = self.exe_attack(squad, pos)
        elif mode == RETREAT_MODE:
            pass
            # TODO: impl
        elif mode == DEFEND_MODE:
            pass
            # TODO: impl
        return actions

    def exe_attack(self, squad, pos):
        actions = list()
        for u in squad:
            if len(self.enemy_units) > 0:
                closest_enemy_dist = math.sqrt(
                    self.cal_square_dist(
                        u, self.find_closest_enemy(u, self.enemy_units)))
                if closest_enemy_dist < self.roach_attack_range and \
                                (u.float_attr.health / u.float_attr.health_max) < 0.3 and \
                                self.find_strongest_unit_hp(squad) > 0.9:
                    action = self.run_away_from_closest_enemy(u, self.enemy_units)
                    # print('micro action works.')
                else:
                    action = self.attack_pos(u, pos)
            else:
                action = self.attack_pos(u, pos)
            actions.append(action)
        return actions

    def find_enemy_base_pos(self, base_pos, minimap):
        if len(base_pos) == 0:
            return [0, 0]

        # [57.5, 27.5] -> mini map 1-dim [40:50] 2-dim [40:50]
        mm = np.asarray(minimap[5])
        minimap_pos1 = mm[15:35, 10:30]
        minimap_pos2 = mm[10:30, 35:55]
        minimap_pos3 = mm[40:60, 5:25]
        minimap_pos4 = mm[40:60, 35:55]

        pos = [(27.5, 59.5), (59.5, 59.5), (27.5, 27.5), (59.5, 27.5)]
        # pos = [(38.5, 122.5), (122.5, 122.5), (38.5, 38.5), (162.5, 18.5)]
        enemy_cnt = list()
        enemy_cnt.append(np.sum(minimap_pos1 == 4))
        enemy_cnt.append(np.sum(minimap_pos2 == 4))
        enemy_cnt.append(np.sum(minimap_pos3 == 4))
        enemy_cnt.append(np.sum(minimap_pos4 == 4))
        self.enemy_pos_cnt_max = max(enemy_cnt)
        #print('enemy_count: ', enemy_cnt)

        if base_pos[0] > base_pos[1]:  # me at bottom-right
            order = [4, 3, 2, 1]
        else:  # me at top-left
            order = [1, 2, 3, 4]
        for each in order:
            if enemy_cnt[each-1] > 5:
                return pos[each-1]

        return pos[order[-1]-1]


class ZergCombatMgr(BaseCombatMgr):
    """ A zvz Zerg combat manager """

    def __init__(self):
        super(ZergCombatMgr, self).__init__()
        self.enemy_pos_cnt_max = 0
        self.roach_attack_range = 5.0
        self.enemy_units = []

    def update(self, dc, am):
        super(ZergCombatMgr, self).update(dc, am)
        actions = list()

        obs = dc.sd.obs
        units = obs['units']
        minimap = obs['minimap']
        self.enemy_units = dc.dd.enemy_pool.units

        hatcheries = collect_units(units, UNIT_TYPEID.ZERG_HATCHERY.value)
        base_pos = [hatcheries[0].float_attr.pos_x, hatcheries[0].float_attr.pos_y] \
            if len(hatcheries) > 0 else [0, 0]
        pos = self.find_enemy_base_pos(base_pos, minimap)

        while True:
            cmds = dc.dd.combat_command_queue.pull()
            if cmds == []:
                break
            else:
                squad = cmds.squad
                actions.extend(self.exe_cmd(squad, pos, ATTACK_MODE))

        am.push_actions(actions)

    def exe_cmd(self, squad, pos, mode):
        actions = []
        if mode == ATTACK_MODE:
            actions = self.exe_attack(squad, pos)
        elif mode == RETREAT_MODE:
            actions = self.exe_retreat(squad, pos)
        elif mode == DEFEND_MODE:
            actions = self.exe_defend(squad, pos)
        return actions

    def exe_attack(self, squad, pos):
        actions = list()
        squad_units = []
        for combat_unit in squad.units:
            squad_units.append(combat_unit.unit)
        for u in squad_units:
            if len(self.enemy_units) > 0:
                closest_enemy_dist = math.sqrt(
                    self.cal_square_dist(
                        u, self.find_closest_enemy(u, self.enemy_units)))
                if (closest_enemy_dist < self.roach_attack_range and
                            (u.float_attr.health / u.float_attr.health_max) < 0.3 and
                            self.find_strongest_unit_hp(squad_units) > 0.9):
                    action = self.run_away_from_closest_enemy(u, self.enemy_units)
                    # print('micro action works.')
                else:
                    action = self.attack_pos(u, pos)
            else:
                action = self.attack_pos(u, pos)
            actions.append(action)
        return actions

    def exe_retreat(self, squad, pos):
        actions = []
        return actions

    def exe_defend(self, squad, pos):
        actions = []
        return actions

    def find_enemy_base_pos(self, base_pos, minimap):
        if len(base_pos) == 0:
            return [0, 0]

        # [57.5, 27.5] -> mini map 1-dim [40:50] 2-dim [40:50]
        mm = np.asarray(minimap[5])
        minimap_pos1 = mm[15:35, 10:30]
        minimap_pos2 = mm[10:30, 35:55]
        minimap_pos3 = mm[40:60, 5:25]
        minimap_pos4 = mm[40:60, 35:55]

        pos = [(24.5, 62.5), (62.5, 62.5), (24.5, 24.5), (62.5, 24.5)]
        # pos = [(38.5, 122.5), (122.5, 122.5), (38.5, 38.5), (162.5, 18.5)]
        enemy_cnt = list()
        enemy_cnt.append(np.sum(minimap_pos1 == 4))
        enemy_cnt.append(np.sum(minimap_pos2 == 4))
        enemy_cnt.append(np.sum(minimap_pos3 == 4))
        enemy_cnt.append(np.sum(minimap_pos4 == 4))
        self.enemy_pos_cnt_max = max(enemy_cnt)
        # print('enemy_count: ', enemy_cnt)

        if base_pos[0] > base_pos[1]:  # me at bottom-right
            order = [4, 3, 2, 1]
        else:  # me at top-left
            order = [1, 2, 3, 4]
        for each in order:
            if enemy_cnt[each-1] > 5:
                return pos[each-1]

        return pos[order[-1]-1]
