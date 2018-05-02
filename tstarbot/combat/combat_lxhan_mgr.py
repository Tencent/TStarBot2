"""A old combat manager for testing"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import numpy as np
from tstarbot.combat.micro.micro_mgr import MicroBase


class ZergCombatLxHanMgr(MicroBase):
    """ A temporal Mgr for testing Combat module for full game """
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
            actions.extend(self.exe_cmd(squad, pos, 'ATTACK'))

        am.push_actions(actions)

    def exe_cmd(self, squad, pos, mode):
        actions = []
        if mode == 'ATTACK':
            actions = self.exe_attack(squad, pos)
        elif mode == 'DEFEND':
            pass
        elif mode == 'RETREAT':
            pass
        return actions

    def exe_attack(self, squad, pos):
        actions = list()
        for u in squad:
            if len(self.enemy_units) > 0:
                closest_enemy_dist = math.sqrt(
                    self.cal_square_dist(u, self.find_closest_enemy(u, self.enemy_units)))
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

        if base_pos[0] > base_pos[1]:  # me at bottom-right
            order = [4, 3, 2, 1]
        else:  # me at top-left
            order = [1, 2, 3, 4]
        for each in order:
            if enemy_cnt[each-1] > 5:
                return pos[each-1]

        return pos[order[-1]-1]
