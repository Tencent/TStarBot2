"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID
from tstarbot.production_strategy.base_zerg_production_mgr import ZergBaseProductionMgr
from tstarbot.production_strategy.util import *


class ZergProdAdvArms(ZergBaseProductionMgr):
    def __init__(self, dc):
        super(ZergProdAdvArms, self).__init__(dc)
        self.ultra_goal = self.get_ultra_goal()

    def get_ultra_goal(self):
        return{UNIT_TYPEID.ZERG_ROACH: 13,
               UNIT_TYPEID.ZERG_HYDRALISK: 20,
               UNIT_TYPEID.ZERG_INFESTOR: 3,
               UNIT_TYPEID.ZERG_CORRUPTOR: 0,
               UNIT_TYPEID.ZERG_LURKERMP: 8,
               UNIT_TYPEID.ZERG_VIPER: 2,
               UNIT_TYPEID.ZERG_RAVAGER: 4,
               UNIT_TYPEID.ZERG_ULTRALISK: 4,
               UNIT_TYPEID.ZERG_MUTALISK: 0,
               UNIT_TYPEID.ZERG_BROODLORD: 0,
               UNIT_TYPEID.ZERG_QUEEN: 3,
               UNIT_TYPEID.ZERG_OVERSEER: 20,
               UNIT_TYPEID.ZERG_DRONE: 66}

    def get_opening_build_order(self):
        return [UNIT_TYPEID.ZERG_DRONE, UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_OVERLORD,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE] + \
               [UNIT_TYPEID.ZERG_HATCHERY, UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_EXTRACTOR] + \
               [UNIT_TYPEID.ZERG_DRONE] * 4 + \
               [UNIT_TYPEID.ZERG_SPAWNINGPOOL,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_ROACHWARREN,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_QUEEN] + \
               [UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_ROACH] * 1 + \
               [UNIT_TYPEID.ZERG_SPINECRAWLER] + \
               [UNIT_TYPEID.ZERG_DRONE,
                UNIT_TYPEID.ZERG_ROACH] * 2 + \
               [UNIT_TYPEID.ZERG_SPINECRAWLER,
                UNIT_TYPEID.ZERG_ROACH,
                UNIT_TYPEID.ZERG_ROACH,
                UNIT_TYPEID.ZERG_SPINECRAWLER]

    def get_goal(self, dc):
        if not self.has_building_built([UNIT_TYPEID.ZERG_LAIR.value,
                                        UNIT_TYPEID.ZERG_HIVE.value]):
            goal = [UNIT_TYPEID.ZERG_LAIR] + \
                   [UNIT_TYPEID.ZERG_DRONE] * 6 + \
                   [UNIT_TYPEID.ZERG_ROACH] * 5 + \
                   [UNIT_TYPEID.ZERG_SPIRE] * 1 + \
                   [UNIT_TYPEID.ZERG_DRONE, UNIT_TYPEID.ZERG_ROACH] * 5 + \
                   [UNIT_TYPEID.ZERG_MUTALISK] * 6 + \
                   [UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER] + \
                   [UNIT_TYPEID.ZERG_ROACH,
                    UNIT_TYPEID.ZERG_DRONE] * 3 + \
                   [UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER] + \
                   [UPGRADE_ID.BURROW,
                    UPGRADE_ID.TUNNELINGCLAWS,
                    UNIT_TYPEID.ZERG_HYDRALISKDEN] + \
                   [UNIT_TYPEID.ZERG_ROACH,
                    UNIT_TYPEID.ZERG_DRONE] * 7
        else:
            num_worker_needed = 0
            num_worker = 0
            bases = dc.dd.base_pool.bases
            for base_tag in bases:
                base = bases[base_tag]
                num_worker += self.assigned_harvesters(base)
                num_worker_needed += self.ideal_harvesters(base)
            num_worker_needed -= num_worker
            game_loop = self.obs['game_loop'][0]

            count = unique_unit_count(self.obs['units'], self.TT)
            if game_loop < 6 * 60 * 16:  # 8 min
                goal = [UNIT_TYPEID.ZERG_ROACH] * 2 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2 + \
                       [UNIT_TYPEID.ZERG_RAVAGER] * 1
            elif game_loop < 12 * 60 * 16:  # 12 min
                goal = [UNIT_TYPEID.ZERG_ROACH] * 1 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2 + \
                       [UNIT_TYPEID.ZERG_RAVAGER] * 1
                if (not self.unit_in_progress(UNIT_TYPEID.ZERG_LURKERDENMP.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_LURKERDENMP.value)):
                    goal += [UNIT_TYPEID.ZERG_LURKERDENMP]

                if self.has_building_built([UNIT_TYPEID.ZERG_LURKERDENMP.value]):
                    diff = self.ultra_goal[UNIT_TYPEID.ZERG_LURKERMP] - count[
                        UNIT_TYPEID.ZERG_LURKERMP.value]
                    if diff > 0:
                        goal += [UNIT_TYPEID.ZERG_LURKERMP] * 2
            else:
                goal = []
                diff = self.ultra_goal[UNIT_TYPEID.ZERG_ROACH] - count[
                    UNIT_TYPEID.ZERG_ROACH.value]
                if diff > 0:
                    goal += [UNIT_TYPEID.ZERG_ROACH] * min(3, diff)

                diff = self.ultra_goal[UNIT_TYPEID.ZERG_RAVAGER] - count[
                    UNIT_TYPEID.ZERG_RAVAGER.value]
                if diff > 0:
                    goal += [UNIT_TYPEID.ZERG_RAVAGER] * min(1, diff)

                diff = self.ultra_goal[UNIT_TYPEID.ZERG_HYDRALISK] - count[
                    UNIT_TYPEID.ZERG_HYDRALISK.value]
                if diff > 0:
                    goal += [UNIT_TYPEID.ZERG_HYDRALISK] * min(3, diff)

                if (not self.unit_in_progress(UNIT_TYPEID.ZERG_SPIRE.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_SPIRE.value)):
                    goal += [UNIT_TYPEID.ZERG_SPIRE]

                if (not self.unit_in_progress(UNIT_TYPEID.ZERG_LURKERDENMP.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_LURKERDENMP.value)):
                    goal += [UNIT_TYPEID.ZERG_LURKERDENMP]

                if self.has_building_built([UNIT_TYPEID.ZERG_LURKERDENMP.value]):
                    diff = self.ultra_goal[UNIT_TYPEID.ZERG_LURKERMP] - count[
                        UNIT_TYPEID.ZERG_LURKERMP.value]
                    if diff > 0:
                        goal += [UNIT_TYPEID.ZERG_LURKERMP] * min(2, diff)
                        # goal += [UNIT_TYPEID.ZERG_LURKERMP] * 2

                if self.has_building_built([UNIT_TYPEID.ZERG_SPIRE.value]) and \
                        self.has_building_built([UNIT_TYPEID.ZERG_HIVE.value]):
                    diff = self.ultra_goal[UNIT_TYPEID.ZERG_VIPER] - count[
                        UNIT_TYPEID.ZERG_VIPER.value]
                    if diff > 0:
                        goal += [UNIT_TYPEID.ZERG_VIPER] * min(1, diff)

                if (not self.unit_in_progress(UNIT_TYPEID.ZERG_INFESTATIONPIT.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_INFESTATIONPIT.value)):
                    goal += [UNIT_TYPEID.ZERG_INFESTATIONPIT]

                if self.has_building_built([UNIT_TYPEID.ZERG_INFESTATIONPIT.value]):
                    diff = self.ultra_goal[UNIT_TYPEID.ZERG_INFESTOR] - count[
                        UNIT_TYPEID.ZERG_INFESTOR.value]
                    if diff > 0:
                        goal += [UNIT_TYPEID.ZERG_INFESTOR] * min(1, diff)

                if (self.has_building_built([UNIT_TYPEID.ZERG_INFESTATIONPIT.value])
                        and not self.unit_in_progress(UNIT_TYPEID.ZERG_HIVE.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_HIVE.value)):
                    goal += [UNIT_TYPEID.ZERG_HIVE]

                # if (self.has_building_built([UNIT_TYPEID.ZERG_HIVE.value])
                #         and not self.unit_in_progress(UNIT_TYPEID.ZERG_GREATERSPIRE.value)
                #         and not self.has_unit(UNIT_TYPEID.ZERG_GREATERSPIRE.value)):
                #     goal += [UNIT_TYPEID.ZERG_GREATERSPIRE]
                # if self.has_building_built([UNIT_TYPEID.ZERG_GREATERSPIRE.value]):
                #     goal += [UNIT_TYPEID.ZERG_CORRUPTOR] * 3

                # ULTRALISK
                if (self.has_building_built([UNIT_TYPEID.ZERG_HIVE.value])
                        and not self.unit_in_progress(UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value)
                        and not self.has_unit(UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value)):
                    goal += [UNIT_TYPEID.ZERG_ULTRALISKCAVERN]

                if self.has_building_built([UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value]):
                    diff = self.ultra_goal[UNIT_TYPEID.ZERG_ULTRALISK] - count[
                        UNIT_TYPEID.ZERG_ULTRALISK.value]
                    if diff > 0:
                        goal += [UNIT_TYPEID.ZERG_ULTRALISK] * min(2, diff)
            if num_worker_needed > 0 and num_worker < 66:
                diff = self.ultra_goal[UNIT_TYPEID.ZERG_DRONE] - count[UNIT_TYPEID.ZERG_DRONE.value]
                if diff > 0:
                    goal = [UNIT_TYPEID.ZERG_DRONE] * min(5, diff) + goal
        return goal
