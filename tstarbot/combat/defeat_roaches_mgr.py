from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import random
import numpy as np
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp

from tstarbot.combat import BaseCombatMgr

ROACH_ATTACK_RANGE = 5.0


class DefeatRoachesCombatMgr(BaseCombatMgr):
    """ Combat Manager for the DefeatRoaches minimap"""

    def __init__(self, dc):
        super(DefeatRoachesCombatMgr, self).__init__(dc)
        self.marines = None
        self.roaches = None

    def update(self, dc, am):
        super(DefeatRoachesCombatMgr, self).update(dc, am)
        self.marines = dc.marines
        self.roaches = dc.roaches

        actions = list()
        for m in self.marines:
            closest_enemy_dist = math.sqrt(self.cal_square_dist(m, self.find_closest_enemy(m, self.roaches)))
            if closest_enemy_dist < ROACH_ATTACK_RANGE and \
                (m.float_attr.health / m.float_attr.health_max) < 0.3 and \
                self.find_strongest_unit_hp(self.marines) > 0.9:
                action = self.run_away_from_closest_enemy(m, self.roaches)
            else:
                action = self.attack_weakest_enemy(m, self.roaches)
            actions.append(action)

        am.push_actions(actions)

