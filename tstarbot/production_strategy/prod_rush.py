"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID
from tstarbot.production_strategy.base_zerg_production_mgr import ZergBaseProductionMgr
from tstarbot.production_strategy.util import *

class ZergProdRush(ZergBaseProductionMgr):
    def __init__(self, dc):
        super(ZergProdRush, self).__init__(dc)

    def get_opening_build_order(self):
        return [UNIT_TYPEID.ZERG_DRONE, UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_OVERLORD, UNIT_TYPEID.ZERG_EXTRACTOR,
                UNIT_TYPEID.ZERG_DRONE, UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_SPAWNINGPOOL] + \
               [UNIT_TYPEID.ZERG_DRONE] * 4 + \
               [UNIT_TYPEID.ZERG_HATCHERY,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_ROACHWARREN,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_QUEEN] + \
               [UNIT_TYPEID.ZERG_ZERGLING] * 2 + \
               [UNIT_TYPEID.ZERG_ROACH] * 5

    def get_goal(self, dc):
        if not self.has_building_built([UNIT_TYPEID.ZERG_LAIR.value,
                                        UNIT_TYPEID.ZERG_HIVE.value]):
            goal = [UNIT_TYPEID.ZERG_LAIR] + \
                   [UNIT_TYPEID.ZERG_DRONE,
                    UNIT_TYPEID.ZERG_ROACH] * 5 + \
                   [UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER] + \
                   [UNIT_TYPEID.ZERG_ROACH,
                    UNIT_TYPEID.ZERG_DRONE] * 2 + \
                   [UPGRADE_ID.BURROW,
                    UNIT_TYPEID.ZERG_HYDRALISKDEN] + \
                   [UNIT_TYPEID.ZERG_ROACH,
                    UNIT_TYPEID.ZERG_DRONE] * 3 + \
                   [UPGRADE_ID.TUNNELINGCLAWS]
        else:
            num_worker_needed = 0
            num_worker = 0
            bases = dc.dd.base_pool.bases
            for base_tag in bases:
                base = bases[base_tag]
                num_worker += self.assigned_harvesters(base)
                num_worker_needed += self.ideal_harvesters(base)
            num_worker_needed -= num_worker
            if num_worker_needed > 0 and num_worker < 66:
                goal = [UNIT_TYPEID.ZERG_DRONE] * 2 + \
                       [UNIT_TYPEID.ZERG_ROACH] * 3 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2
            else:
                goal = [UNIT_TYPEID.ZERG_ROACH] * 3 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2
            # add some ravager
            game_loop = self.obs['game_loop'][0]
            if game_loop > 6 * 60 * 16:  # 8 min
                goal += [UNIT_TYPEID.ZERG_RAVAGER] * 2
        return goal
