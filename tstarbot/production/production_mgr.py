"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import operator

from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import ABILITY_ID
from pysc2.lib.typeenums import UPGRADE_ID
from pysc2.lib.typeenums import RACE
from collections import namedtuple
from tstarbot.data.pool.map_tool import compute_area_dist
from tstarbot.data.pool.macro_def import BASE_UNITS
from tstarbot.production.util import *
import distutils.version

BuildCmdBuilding = namedtuple('build_cmd_building', ['base_tag', 'unit_type'])
BuildCmdUnit = namedtuple('build_cmd_unit', ['base_tag', 'unit_type'])
BuildCmdUpgrade = namedtuple('build_cmd_upgrade', ['building_tag',
                                                   'ability_id'])
BuildCmdMorph = namedtuple('build_cmd_morph', ['unit_tag',
                                               'ability_id'])
BuildCmdExpand = namedtuple('build_cmd_expand', ['base_tag', 'pos'])
BuildCmdHarvest = namedtuple('build_cmd_harvest', ['gas_first'])
BuildCmdSpawnLarva = namedtuple('build_cmd_spawn_larva',
                                ['base_tag', 'queen_tag'])


class BaseProductionMgr(object):
    def __init__(self, dc, race=RACE.Zerg, use_search=True):
        self.onStart = True
        self.race = race
        self.use_search = use_search
        self.TT = dc.sd.TT
        self.build_order = BuildOrderQueue(self.TT)
        self.obs = None
        self.cut_in_item = []
        self.born_pos = None
        self.verbose = 0
        self.strategy = 'RUSH'
        self._init_config(dc)

    def _init_config(self, dc):
        if hasattr(dc, 'config'):
            if hasattr(dc.config, 'production_verbose'):
                self.verbose = dc.config.production_verbose
            if hasattr(dc.config, 'production_strategy'):
                self.strategy = dc.config.production_strategy

    def reset(self):
        self.onStart = True
        self.build_order.clear_all()
        self.obs = None
        self.cut_in_item = []
        self.born_pos = None

    def update(self, data_context, act_mgr):
        self.obs = data_context.sd.obs

        # Get goal and search build order
        if self.onStart:
            self.build_order.set_build_order(self.get_opening_build_order())
            bases = data_context.dd.base_pool.bases
            self.born_pos = [[bases[tag].unit.float_attr.pos_x,
                              bases[tag].unit.float_attr.pos_y]
                             for tag in bases][0]
            self.onStart = False
        elif self.build_order.is_empty():
            goal = self.get_goal(data_context)
            if self.use_search:
                self.build_order.set_build_order(self.perform_search(goal))
            else:
                self.build_order.set_build_order(goal)

        # determine whether to Expand
        if (self.base_unit() not in self.cut_in_item
                and self.should_expand_now(data_context)):
            self.build_order.queue_as_highest(self.base_unit())
            self.cut_in_item.append(self.base_unit())
            if self.verbose > 0:
                print('Cut in: {}'.format(self.base_unit()))

        # determine whether to build extractor
        if (self.gas_unit() not in self.cut_in_item
                and self.need_more_extractor(data_context)):
            self.build_order.queue_as_highest(self.gas_unit())
            self.cut_in_item.append(self.gas_unit())
            if self.verbose > 0:
                print('Cut in: {}'.format(self.gas_unit()))

        self.add_upgrade(data_context)

        self.post_update(data_context)

        # deal with the dead lock if exists (supply, uprade, tech ...)
        if not self.build_order.is_empty():
            while self.detect_dead_lock(data_context):
                pass

        self.check_supply(data_context)

        # check resource, builder, requirement and determine the build base
        current_item = self.build_order.current_item()
        if current_item and self.can_build(current_item, data_context):
            if current_item.isUnit:
                if self.set_build_base(current_item, data_context):
                    self.build_order.remove_current_item()
                    if current_item.unit_id in self.cut_in_item:
                        self.cut_in_item.remove(current_item.unit_id)
                    if self.verbose > 0:
                        print('Produce: {}'.format(current_item.unit_id))
            else:  # Upgrade
                if self.upgrade(current_item, data_context):
                    self.build_order.remove_current_item()
                    if current_item.unit_id in self.cut_in_item:
                        self.cut_in_item.remove(current_item.unit_id)
                    if self.verbose > 0:
                        print('Upgrade: {}'.format(current_item.unit_id))

        if self.should_gas_first(data_context):
            data_context.dd.build_command_queue.put(
                BuildCmdHarvest(gas_first=True))

        if self.should_mineral_first(data_context):
            data_context.dd.build_command_queue.put(
                BuildCmdHarvest(gas_first=False))

    def supply_unit(self):
        if self.race == RACE.Zerg:
            return UNIT_TYPEID.ZERG_OVERLORD
        if self.race == RACE.Protoss:
            return UNIT_TYPEID.PROTOSS_PYLON
        if self.race == RACE.Terran:
            return UNIT_TYPEID.TERRAN_SUPPLYDEPOT
        raise Exception("Race type Error. typeenums.RACE.")

    def gas_unit(self):
        if self.race == RACE.Zerg:
            return UNIT_TYPEID.ZERG_EXTRACTOR
        if self.race == RACE.Protoss:
            return UNIT_TYPEID.PROTOSS_ASSIMILATOR
        if self.race == RACE.Terran:
            return UNIT_TYPEID.TERRAN_REFINERY
        raise Exception("Race type Error. typeenums.RACE.")

    def base_unit(self):
        if self.race == RACE.Zerg:
            return UNIT_TYPEID.ZERG_HATCHERY
        if self.race == RACE.Protoss:
            return UNIT_TYPEID.PROTOSS_NEXUS
        if self.race == RACE.Terran:
            return UNIT_TYPEID.TERRAN_COMMANDCENTER
        raise Exception("Race type Error. typeenums.RACE.")

    def detect_dead_lock(self, data_context):
        current_item = self.build_order.current_item()
        builder = None
        for unit_type in current_item.whatBuilds:
            if (self.has_unit(unit_type)
                    or self.unit_in_progress(unit_type)
                    or unit_type == UNIT_TYPEID.ZERG_LARVA.value):
                builder = unit_type
                break
        if builder is None and len(current_item.whatBuilds) > 0:
            builder_id = [unit_id for unit_id in UNIT_TYPEID
                          if unit_id.value == current_item.whatBuilds[0]]
            self.build_order.queue_as_highest(builder_id[0])
            if self.verbose > 0:
                print('Cut in: {}'.format(builder_id[0]))
            return True
        required_unit = None
        for unit_type in current_item.requiredUnits:
            if (self.has_unit(unit_type)
                    or self.unit_in_progress(unit_type)):
                required_unit = unit_type
                break
        if required_unit is None and len(current_item.requiredUnits) > 0:
            required_id = [unit_id for unit_id in UNIT_TYPEID
                           if unit_id.value == current_item.requiredUnits[0]]
            self.build_order.queue_as_highest(required_id[0])
            if self.verbose > 0:
                print('Cut in: {}'.format(required_id[0]))
            return True
        required_upgrade = None
        for upgrade_type in current_item.requiredUpgrades:
            if (not self.has_upgrade(data_context, [upgrade_type])
                    and not self.upgrade_in_progress(upgrade_type)):
                required_upgrade = upgrade_type
                break
        if required_upgrade is not None:
            required_id = [up_id for up_id in UPGRADE_ID
                           if up_id.value == required_upgrade]
            self.build_order.queue_as_highest(required_id[0])
            if self.verbose > 0:
                print('Cut in: {}'.format(required_id[0]))
        return False

    def check_supply(self, dc):
        play_info = self.obs["player"]
        current_item = self.build_order.current_item()
        # No enough supply and supply not in building process
        if (current_item is not None
                and play_info[3] + current_item.supplyCost
                    > play_info[4] - min(20, max(0, (play_info[4]-30)/5))
                and current_item.supplyCost > 0
                and not self.supply_in_progress()
                and current_item.unit_id != self.supply_unit()
                and play_info[4] < 200):
            self.build_order.queue_as_highest(self.supply_unit())
            if self.verbose > 0:
                print('Cut in: {}'.format(self.supply_unit()))

    def has_unit(self, unit_type, alliance=1):
        return any([(unit.unit_type == unit_type and unit.int_attr.alliance == alliance)
                    for unit in self.obs["units"]])

    def find_unit(self, unit_type, alliance=1):
        return [unit for unit in self.obs["units"]
                if unit.unit_type == unit_type
                and unit.int_attr.alliance == alliance]

    def has_building_built(self, unit_type_list, alliance=1):
        for unit_type in unit_type_list:
            for unit in self.obs["units"]:
                if (unit.unit_type == unit_type
                        and unit.int_attr.alliance == alliance
                        and unit.float_attr.build_progress == 1):
                    return True
        return len(unit_type_list) == 0

    def has_upgrade(self, dc, upgrade_type_list):
        return (all([up_type in dc.sd.obs['raw_data'].player.upgrade_ids
                     for up_type in upgrade_type_list])
                or len(upgrade_type_list) == 0)

    def upgrade_in_progress(self, upgrade_type, alliance=1):
        data = self.TT.getUpgradeData(upgrade_type)
        builders = [unit for unit in self.obs['units']
                    if unit.unit_type in data.whatBuilds
                    and unit.int_attr.alliance == alliance]
        in_progress = [builder for builder in builders
                       if len(builder.orders) > 0
                       and builder.orders[0].ability_id == data.buildAbility]
        return in_progress

    def unit_in_progress(self, unit_type, alliance=1):
        data = self.TT.getUnitData(unit_type)
        order_unit = data.whatBuilds
        if UNIT_TYPEID.ZERG_LARVA.value in order_unit:
            order_unit = [UNIT_TYPEID.ZERG_EGG.value]
        for unit in self.obs['units']:
            if (unit.unit_type == unit_type
                    and unit.int_attr.alliance == alliance
                    and unit.float_attr.build_progress < 1):
                return True
            if (unit.unit_type in order_unit
                    and unit.int_attr.alliance == alliance
                    and len(unit.orders) > 0
                    and unit.orders[0].ability_id == data.buildAbility):
                return True
        return False

    def should_expand_now(self, data_context):
        return False

    def need_more_extractor(self, data_context):
        return False

    def get_opening_build_order(self):
        return []

    def perform_search(self, goal):  # TODO: implement search algorithm here
        return goal

    def get_goal(self, dc):
        return []

    def add_upgrade(self, dc):
        pass

    def post_update(self, dc):
        pass

    def set_build_base(self, build_item, data_context):
        return False

    def upgrade(self, build_item, data_context):
        return False

    def can_build(self, build_item, data_context):  # check resource requirement
        return False

    def supply_in_progress(self):
        return self.unit_in_progress(self.supply_unit().value)

    def should_gas_first(self, dc):
        return True

    def should_mineral_first(self, dc):
        return False


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self, dc):
        super(ZergProductionMgr, self).__init__(dc)
        self.ultra_goal = {UNIT_TYPEID.ZERG_ROACH: 15,
                           UNIT_TYPEID.ZERG_HYDRALISK: 22,
                           UNIT_TYPEID.ZERG_INFESTOR: 3,
                           UNIT_TYPEID.ZERG_CORRUPTOR: 0,
                           UNIT_TYPEID.ZERG_LURKERMP: 8,
                           UNIT_TYPEID.ZERG_VIPER: 2,
                           UNIT_TYPEID.ZERG_RAVAGER: 4,
                           UNIT_TYPEID.ZERG_ULTRALISK: 4,
                           UNIT_TYPEID.ZERG_MUTALISK: 3,
                           UNIT_TYPEID.ZERG_BROODLORD: 0,
                           UNIT_TYPEID.ZERG_QUEEN: 3,
                           UNIT_TYPEID.ZERG_OVERSEER: 20,
                           UNIT_TYPEID.ZERG_DRONE: 66}

    def reset(self):
        super(ZergProductionMgr, self).reset()

    def update(self, data_context, act_mgr):
        super(ZergProductionMgr, self).update(data_context, act_mgr)
        self.spawn_larva(data_context)

        actions = []
        act_mgr.push_actions(actions)

    def get_goal_long_game(self, dc):
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
            elif game_loop < 12 * 60 * 16: # 12 min
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


                # goal = [UNIT_TYPEID.ZERG_ROACH] * 3 + \
                #        [UNIT_TYPEID.ZERG_RAVAGER] * 2 + \
                #        [UNIT_TYPEID.ZERG_HYDRALISK] * 3 + \
                #        [UNIT_TYPEID.ZERG_VIPER] * 1 + [UNIT_TYPEID.ZERG_INFESTOR] * 1
                #        [UNIT_TYPEID.ZERG_OVERSEER] * 1
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
                    #goal += [UNIT_TYPEID.ZERG_LURKERMP] * 2

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
                if (self.has_building_built([UNIT_TYPEID.ZERG_HIVE.value]) and
                        not self.unit_in_progress(UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value)
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

    def get_goal_rush(self, dc):
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
                goal = [UNIT_TYPEID.ZERG_DRONE] * 2 +\
                       [UNIT_TYPEID.ZERG_ROACH] * 3 +\
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2
            else:
                goal = [UNIT_TYPEID.ZERG_ROACH] * 3 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK] * 2
            # add some ravager
            game_loop = self.obs['game_loop'][0]
            if game_loop > 6 * 60 * 16:  # 8 min
                goal += [UNIT_TYPEID.ZERG_RAVAGER] * 2
        return goal

    def get_goal(self, dc):
        if self.strategy == 'RUSH':
            return self.get_goal_rush(dc)
        elif self.strategy == 'ADV_ARMS':
            return self.get_goal_long_game(dc)
        else:
            raise Exception('Unknow production strategy!')

    def perform_search(self, goal):
        return goal

    def get_opening_build_order(self):
        if self.strategy == 'RUSH':
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
        elif self.strategy == 'ADV_ARMS':
            return [UNIT_TYPEID.ZERG_DRONE, UNIT_TYPEID.ZERG_DRONE,
                    UNIT_TYPEID.ZERG_OVERLORD,
                    UNIT_TYPEID.ZERG_DRONE,
                    UNIT_TYPEID.ZERG_DRONE] + \
                   [UNIT_TYPEID.ZERG_HATCHERY,
                    UNIT_TYPEID.ZERG_EXTRACTOR, UNIT_TYPEID.ZERG_DRONE] + \
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
        else:
            raise Exception('Unknow production strategy!')

    def should_expand_now(self, dc):
        if self.strategy == 'ADV_ARMS':
            expand_worker = {0: 0, 1: 20, 2: 28, 3: 40, 4: 45,
                             5: 50, 6: 55, 7: 60, 8: 64, 9: 65,
                             10: 65, 11: 65, 12: 200}
        else:
            expand_worker = {0: 0, 1: 20, 2: 33, 3: 40, 4: 45,
                             5: 50, 6: 55, 7: 60, 8: 200}
        num = len([unit for unit in self.obs['units']
                   if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_DRONE.value
                   and unit.int_attr.alliance == 1])
        bases = dc.dd.base_pool.bases
        ideal_harvesters_all = 0
        base_num = 0
        for base_tag in bases:
            base_num += 1
            if bases[base_tag].unit.float_attr.build_progress == 1:
                ideal_harvesters_all += self.ideal_harvesters(bases[base_tag])
        base_num = min(12, base_num)
        if (num > min(ideal_harvesters_all, expand_worker[base_num])
                and not self.unit_in_progress(self.base_unit().value)):
            return True
        return False

    def need_more_extractor(self, dc):
        gas_worker_num = {1: 19, 2: 25, 3: 30, 4: 35, 5: 40}
        bases = dc.dd.base_pool.bases
        n_w = len([unit for unit in self.obs['units']
                   if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_DRONE.value
                   and unit.int_attr.alliance == 1])
        n_g = len([u for u in self.obs['units']
                   if u.unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value
                   and u.int_attr.vespene_contents > 100
                   and u.int_attr.alliance == 1])  # 100 gas ~ 30s ?
        if self.unit_in_progress(UNIT_TYPEID.ZERG_EXTRACTOR.value):
            return False

        gas_num = 0
        for base_tag in bases:
            if (bases[base_tag].unit.float_attr.build_progress < 1
                    or len(bases[base_tag].worker_set) == 0):
                continue
            gas_num += 2 - len(bases[base_tag].vb_set)
        if gas_num == 0:
            return False

        if n_g == 0:
            current_item = self.build_order.current_item()
            if current_item.gasCost > 0:
                return True
        if 0 < n_g < 6 and n_w >= gas_worker_num[n_g]:
            return True
        play_info = self.obs["player"]
        minerals, vespene = play_info[1:3]
        if n_g >= 6 and (minerals > 1000 and vespene < 200):
            return True
        return False

    def post_update(self, dc):
        if (UNIT_TYPEID.ZERG_QUEEN not in self.cut_in_item
                and self.need_more_queen(dc)):
            # print('need more queens!')
            self.build_order.queue_as_highest(UNIT_TYPEID.ZERG_QUEEN)
            self.cut_in_item.append(UNIT_TYPEID.ZERG_QUEEN)
            if self.verbose > 0:
                print('Cut in: {}'.format(UNIT_TYPEID.ZERG_QUEEN))

    def need_more_queen(self, dc):
        if self.unit_in_progress(UNIT_TYPEID.ZERG_QUEEN.value):
            return False
        n_q = len([unit for unit in self.obs['units']
                   if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_QUEEN.value
                   and unit.int_attr.alliance == 1])
        bases = dc.dd.base_pool.bases
        n_base = len([tag for tag in bases
                      if bases[tag].unit.float_attr.build_progress == 1])
        n_army = len([u for u in self.obs['units']
                      if (u.unit_type == UNIT_TYPEID.ZERG_ROACH.value
                          or u.unit_type == UNIT_TYPEID.ZERG_HYDRALISK.value)
                      and u.int_attr.alliance == 1])
        if n_army > 12 and n_q < min(n_base, 3):
            return True
        return False

    def spawn_larva(self, dc):
        queens = self.find_unit(UNIT_TYPEID.ZERG_QUEEN.value)
        for queen in queens:
            if (queen.float_attr.energy > 25
                    and len(queen.orders) == 0):
                bases = dc.dd.base_pool.bases
                base = find_nearest([bases[tag].unit for tag in bases], queen)
                if base is not None:
                    dc.dd.build_command_queue.put(
                        BuildCmdSpawnLarva(queen_tag=queen.tag,
                                           base_tag=base.tag))

    def building_in_progress(self, unit_id, alliance=1):
        unit_data = self.TT.getUnitData(unit_id.value)
        if not unit_data.isBuilding:
            print('building_in_progress can only be used for buildings!')
        for unit in self.obs['units']:
            if (unit.unit_type == unit_id.value
                    and unit.int_attr.alliance == alliance
                    and unit.float_attr.build_progress < 1):
                return True
            if (unit.unit_type == UNIT_TYPEID.ZERG_DRONE.value
                    and unit.int_attr.alliance == alliance
                    and len(unit.orders) > 0
                    and unit.orders[0].ability_id == unit_data.buildAbility):
                return True
        return False

    def queen_in_progress(self, dc):
        data = self.TT.getUnitData(UNIT_TYPEID.ZERG_QUEEN.value)
        bases = dc.dd.base_pool.bases
        for tag in bases:
            if any([order.ability_id == data.buildAbility
                    for order in bases[tag].unit.orders]):
                return True
        return False

    def can_build(self, build_item, dc):  # check resource requirement
        if not (self.has_building_built(build_item.whatBuilds)
                and self.has_building_built(build_item.requiredUnits)
                and self.has_upgrade(dc, build_item.requiredUpgrades)):
            return False
        play_info = self.obs["player"]
        if (build_item.supplyCost > 0
                and play_info[3] + build_item.supplyCost > play_info[4]):
            return False
        return (self.obs['player'][1] >= build_item.mineralCost
                and self.obs['player'][2] >= build_item.gasCost)

    def set_build_base(self, build_item, data_context):
        bases = data_context.dd.base_pool.bases
        builders = build_item.whatBuilds
        if build_item.isBuilding:  # build building
            if UNIT_TYPEID.ZERG_DRONE.value not in builders: # morph building
                build_units = [u for u in self.obs['units']
                              if u.unit_type in builders]
                build_unit = find_nearest_to_pos(build_units, self.born_pos)
                data_context.dd.build_command_queue.put(
                    BuildCmdMorph(unit_tag=build_unit.tag,
                                  ability_id=build_item.buildAbility))
                return True
            if build_item.unit_id == UNIT_TYPEID.ZERG_EXTRACTOR:
                tag = self.find_base_to_build_extractor(bases)
            elif build_item.unit_id == UNIT_TYPEID.ZERG_SPINECRAWLER:
                tag = self.find_base_to_build_spinecrawler(bases)
            else:
                tag = self.find_base_to_build(bases)
            if tag is not None:
                if build_item.unit_id == UNIT_TYPEID.ZERG_HATCHERY:
                    pos = self.find_base_pos(data_context)
                    if pos is not None:
                        data_context.dd.build_command_queue.put(
                            BuildCmdExpand(base_tag=tag, pos=pos))
                else:
                    data_context.dd.build_command_queue.put(
                        BuildCmdBuilding(base_tag=tag,
                                         unit_type=build_item.unit_id.value))
                return True
        else:  # build unit
            if (UNIT_TYPEID.ZERG_LARVA.value not in builders
                    and UNIT_TYPEID.ZERG_HATCHERY.value not in builders):
                build_units = [u for u in self.obs['units']
                              if u.unit_type in builders]
                build_unit = find_nearest_to_pos(build_units, self.born_pos)
                data_context.dd.build_command_queue.put(
                    BuildCmdMorph(unit_tag=build_unit.tag,
                                  ability_id=build_item.buildAbility))
                return True
            if build_item.unit_id == UNIT_TYPEID.ZERG_DRONE:
                tag = self.find_base_to_produce_drone(bases)
            elif build_item.unit_id == UNIT_TYPEID.ZERG_QUEEN:
                tag = self.find_base_to_produce_queue(bases)
            else:
                tag = self.find_base_to_produce_unit(bases)
            if tag is not None:
                data_context.dd.build_command_queue.put(
                    BuildCmdUnit(base_tag=tag,
                                 unit_type=build_item.unit_id.value))
                return True
        return False

    def find_base_to_build_extractor(self, bases):
        max_num = 0  # find base with most workers and need extractor
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            worker_num = self.assigned_harvesters(bases[base_tag])
            if worker_num > max_num and len(bases[base_tag].vb_set) < 2:
                tag = base_tag
                max_num = worker_num
        return tag

    def find_base_with_most_workers(self, bases):
        max_num = 0  # find base with most workers
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            worker_num = self.assigned_harvesters(bases[base_tag])
            if worker_num > max_num:
                tag = base_tag
                max_num = worker_num
        return tag

    def find_base_to_build(self, bases):
        d_min = 1000  # find base closed to born position
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            worker_num = self.assigned_harvesters(bases[base_tag])
            d = dist_to_pos(bases[base_tag].unit, self.born_pos)
            if worker_num > 0 and d < d_min:
                tag = base_tag
                d_min = d
        return tag

    def find_base_to_build_spinecrawler(self, bases):
        d_max = -1  # find base furthest to born position
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            worker_num = self.assigned_harvesters(bases[base_tag])
            d = dist_to_pos(bases[base_tag].unit, self.born_pos)
            if worker_num > 0 and d > d_max:
                tag = base_tag
                d_max = d
        return tag

    def find_base_to_produce_drone(self, bases):
        max_gap = -200  # find base need worker most
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            num_gap = (self.ideal_harvesters(bases[base_tag])
                       - self.assigned_harvesters(bases[base_tag]))
            if (num_gap > max_gap
                    and len(bases[base_tag].larva_set) > 0):
                tag = base_tag
                max_gap = num_gap
        return tag

    def find_base_to_produce_queue(self, bases):
        max_gap = -200  # find base not in morph and need worker most
        max_queen = 20
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            orders = bases[base_tag].unit.orders
            num_gap = (self.ideal_harvesters(bases[base_tag])
                       - self.assigned_harvesters(bases[base_tag]))
            queen_num = len(bases[base_tag].queen_set)
            if (len(orders) == 0
                    and (queen_num < max_queen
                         or (queen_num == max_queen and num_gap > max_gap))):
                tag = base_tag
                max_gap = num_gap
                max_queen = queen_num
        return tag

    def find_base_to_produce_unit(self, bases):
        larva_count = 0  # find base with most larvas
        tag = None
        for base_tag in bases:
            if bases[base_tag].unit.float_attr.build_progress < 1:
                continue
            num_larva = len(bases[base_tag].larva_set)
            if num_larva > larva_count:
                tag = base_tag
                larva_count = num_larva
        return tag

    def find_base_pos_old(self, dc):
        areas = dc.dd.base_pool.resource_cluster
        bases = dc.dd.base_pool.bases
        d_min = 10000
        pos = None
        for area in areas:
            if area not in [base.resource_area for base in bases.values()]:
                d = dc.dd.base_pool.home_dist[area]
                if 5 < d < d_min:
                    pos = area.ideal_base_pos
                    d_min = d
        return pos

    def find_base_pos(self, dc):
        areas = dc.dd.base_pool.resource_cluster
        bases = [unit for unit in self.obs['units']
                    if unit.unit_type in BASE_UNITS]
        d_min = 10000
        pos = None
        for area in areas:
            dist = [dist_to_pos(base, area.ideal_base_pos) for base in bases]
            if min(dist) > 5: # area do not have a base now
                d = dc.dd.base_pool.home_dist[area]
                if 5 < d < d_min:
                    pos = area.ideal_base_pos
                    d_min = d
        return pos

    def find_base_pos_aggressive(self, dc):
        areas = dc.dd.base_pool.resource_cluster
        bases = [unit for unit in self.obs['units']
                    if unit.unit_type in BASE_UNITS]
        if len(dc.dd.base_pool.bases) < 4:
            sorted_area = sorted(dc.dd.base_pool.home_dist.items(),
                                 key=operator.itemgetter(1))
        else:
            sorted_area = sorted(dc.dd.base_pool.enemy_home_dist.items(),
                                 key=operator.itemgetter(1))
            sorted_area = sorted_area[4:]
        sorted_pos_list = [x[0].ideal_base_pos for x in sorted_area]
        for area_pos in sorted_pos_list:
            dist = [dist_to_pos(base, area_pos) for base in bases]
            if min(dist) > 5: # area do not have a base now
                return area_pos
        return None

    def find_unit_by_tag(self, tag):
        return [unit for unit in self.obs['units'] if unit.tag == tag]

    def ideal_harvesters(self, base_item):
        num = base_item.unit.int_attr.ideal_harvesters
        for vb_tag in base_item.vb_set:
            vb = self.find_unit_by_tag(vb_tag)[0]
            num += vb.int_attr.ideal_harvesters
        return num

    def assigned_harvesters(self, base_item):
        num = base_item.unit.int_attr.assigned_harvesters
        for vb_tag in base_item.vb_set:
            vb = self.find_unit_by_tag(vb_tag)[0]
            num += vb.int_attr.assigned_harvesters
        return num

    def should_gas_first(self, dc):
        play_info = self.obs["player"]
        minerals, vespene = play_info[1:3]
        if minerals > 400 and vespene < minerals/3:
            return True
        return False

    def should_mineral_first(self, dc):
        play_info = self.obs["player"]
        minerals, vespene = play_info[1:3]
        if vespene > 300 and minerals < 2 * vespene:
            return True
        return False

    def add_upgrade(self, dc):
        upgrade_list = [UPGRADE_ID.ZERGGROUNDARMORSLEVEL1,
                        UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL1,
                        UPGRADE_ID.CHITINOUSPLATING,
                        UPGRADE_ID.ZERGGROUNDARMORSLEVEL2,
                        UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL2]
        if (distutils.version.LooseVersion(dc.sd.game_version)
                >= distutils.version.LooseVersion('4.1.4')):
            upgrade_list.append(UPGRADE_ID.EVOLVEGROOVEDSPINES)
        upgrade_list.extend([UPGRADE_ID.ZERGGROUNDARMORSLEVEL3,
                             UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL3,
                             UPGRADE_ID.EVOLVEMUSCULARAUGMENTS,
                             UPGRADE_ID.ZERGMELEEWEAPONSLEVEL1,
                             UPGRADE_ID.ZERGMELEEWEAPONSLEVEL2,
                             UPGRADE_ID.ZERGMELEEWEAPONSLEVEL3])

        for upgrade_id in upgrade_list:
            build_item = self.TT.getUpgradeData(upgrade_id.value)
            if (not self.has_building_built(build_item.whatBuilds) or
                    not self.has_building_built(build_item.requiredUnits) or
                    not self.has_upgrade(dc, build_item.requiredUpgrades)):
                continue
            if self.upgrade_in_progress(upgrade_id.value):
                continue
            if self.has_upgrade(dc, [upgrade_id.value]):
                continue
            else:
                if (upgrade_id not in self.cut_in_item and
                        self.find_spare_building(build_item.whatBuilds)):
                    self.build_order.queue_as_highest(upgrade_id)
                    self.cut_in_item.append(upgrade_id)
                    if self.verbose > 0:
                        print('Cut in: {}'.format(upgrade_id))
                break

    def find_spare_building(self, unit_type_list):
        for unit_type in unit_type_list:
            units = self.find_unit(unit_type)
            for unit in units:
                if (len(unit.orders) == 0
                        and unit.float_attr.build_progress == 1):
                    return unit
        return None

    def upgrade(self, build_item, dc):
        builder_list = build_item.whatBuilds
        builder = self.find_spare_building(builder_list)
        if builder is not None:
            dc.dd.build_command_queue.put(
                BuildCmdUpgrade(building_tag=builder.tag,
                                ability_id=build_item.buildAbility))
            return True
        return False
