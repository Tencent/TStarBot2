"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, RACE
from pysc2.lib import TechTree
from collections import deque, namedtuple
from tstarbot.production.map_tool import *

TT = TechTree()

BuildCmdBuilding = namedtuple('build_cmd_building', ['base_tag', 'unit_type'])
BuildCmdUnit = namedtuple('build_cmd_unit', ['base_tag', 'unit_type'])
BuildCmdExpand = namedtuple('build_cmd_expand', ['base_tag', 'pos'])
BuildCmdHarvest = namedtuple('build_cmd_harvest', ['gas_first'])


def dist_to_pos(unit, pos):
    return ((unit.float_attr.pos_x - pos[0])**2 +
            (unit.float_attr.pos_y - pos[1])**2)**0.5


class BuildOrderQueue(object):
    def __init__(self):
        self.queue = deque()

    def set_build_order(self, unit_list):
        for unit_id in unit_list:
            build_item = TT.getUnitData(unit_id)
            build_item.unit_id = unit_id
            self.queue.append(build_item)

    def size(self):
        return len(self.queue)

    def is_empty(self):
        return len(self.queue) == 0

    def current_item(self):
        if len(self.queue) > 0:
            return self.queue[0]
        else:
            return None

    def remove_current_item(self):
        if len(self.queue) > 0:
            self.queue.popleft()

    def queue_as_highest(self, unit_id):
        build_item = TT.getUnitData(unit_id)
        build_item.unit_id = unit_id
        self.queue.appendleft(build_item)

    def queue(self, unit_id):
        build_item = TT.getUnitData(unit_id)
        build_item.unit_id = unit_id
        self.queue.append(build_item)

    def clear_all(self):
        self.queue.clear()

    def reset(self):
        self.queue.clear()


class BaseProductionMgr(object):
    def __init__(self, race=RACE.Zerg, use_search=True):
        self.onStart = True
        self.race = race
        self.use_search = use_search
        self.build_order = BuildOrderQueue()
        self.obs = None

    def reset(self):
        self.onStart = True
        self.build_order.clear_all()
        self.obs = None

    def update(self, data_context, act_mgr):
        self.obs = data_context.sd.obs

        # Get goal and search build order
        if self.onStart:
            self.build_order.set_build_order(self.get_opening_build_order())
            self.onStart = False
        elif self.build_order.is_empty():
            goal = self.get_goal(data_context)
            if self.use_search:
                self.build_order.set_build_order(self.perform_search(goal))
            else:
                self.build_order.set_build_order(goal)

        # determine whether to Expand
        if self.should_expand_now(data_context):
            self.build_order.queue_as_highest(self.base_unit())

        # deal with the dead lock if exists (supply, uprade, tech ...)
        if not self.build_order.is_empty():
            while self.detect_dead_lock(data_context):
                pass

        self.check_supply(data_context)

        # check resource, builder, requirement and determine the build base
        current_item = self.build_order.current_item()
        if self.can_build(current_item, data_context):
            if self.set_build_base(current_item, data_context):
                self.build_order.remove_current_item()

    def supply_unit(self):
        if self.race == RACE.Zerg:
            return UNIT_TYPEID.ZERG_OVERLORD.value
        if self.race == RACE.Protoss:
            return UNIT_TYPEID.PROTOSS_PYLON.value
        if self.race == RACE.Terran:
            return UNIT_TYPEID.TERRAN_SUPPLYDEPOT.value
        raise Exception("Race type Error. typeenums.RACE.")

    def base_unit(self):
        if self.race == RACE.Zerg:
            return UNIT_TYPEID.ZERG_HATCHERY.value
        if self.race == RACE.Protoss:
            return UNIT_TYPEID.PROTOSS_NEXUS.value
        if self.race == RACE.Terran:
            return UNIT_TYPEID.TERRAN_COMMANDCENTER.value
        raise Exception("Race type Error. typeenums.RACE.")

    def detect_dead_lock(self, data_context):
        current_item = self.build_order.current_item()
        builder = None
        for unit_id in current_item.whatBuilds:
            # if unit_id in data_contxt.units_pool
            if (self.has_unit(unit_id) or
                    unit_id == UNIT_TYPEID.ZERG_LARVA.value):
                builder = unit_id
                break
        if builder is None and len(current_item.whatBuilds) > 0:
            self.build_order.queue_as_highest(current_item.whatBuilds[0])
            return True
        required_unit = None
        for unit_id in current_item.requiredUnits:
            # if unit_id in data_context.units_pool
            if self.has_unit(unit_id):
                required_unit = unit_id
                break
        if required_unit is None and len(current_item.requiredUnits) > 0:
            self.build_order.queue_as_highest(current_item.requiredUnits[0])
            return True
        # TODO: add Tech upgrade
        return False

    def check_supply(self, dc):
        play_info = self.obs["player"]
        current_item = self.build_order.current_item()
        # No enough supply and supply not in building process
        if (play_info[3] + current_item.supplyCost
                > play_info[4] - min(6, max(0, (play_info[4]-30)/10))
                and not self.supply_in_progress(dc)
                and current_item.unit_id != self.supply_unit()):
            self.build_order.queue_as_highest(self.supply_unit())

    def has_unit(self, unit_id, owner=1):
        return any([unit.unit_type == unit_id and unit.int_attr.owner == owner
                    for unit in self.obs["units"]])

    def has_building_built(self, unit_id_list, owner=1):
        for unit_id in unit_id_list:
            for unit in self.obs["units"]:
                if (unit.unit_type == unit_id
                        and unit.int_attr.owner == owner
                        and unit.float_attr.build_progress == 1):
                    return True
        return len(unit_id_list) == 0

    def building_in_progress(self, unit_type, owner=1):
        unit_data = TT.getUnitData(unit_type)
        if not unit_data.isBuilding:
            print('building_in_progress can only be used for buildings!')
        for unit in self.obs['units']:
            if (unit.unit_type == unit_type
                    and unit.int_attr.owner == owner
                    and unit.float_attr.build_progress < 1):
                return True
            if (unit.unit_type == UNIT_TYPEID.ZERG_DRONE.value
                    and unit.int_attr.owner == owner
                    and len(unit.orders) > 0
                    and unit.orders[0].ability_id == unit_data.buildAbility):
                return True
        return False

    def should_expand_now(self, data_context):
        return False

    def get_opening_build_order(self):
        return []

    def perform_search(self, goal):  # TODO: implement search algorithm here
        return goal

    def get_goal(self, dc):
        return []

    def set_build_base(self, build_item, data_context):
        pass  # raise NotImplementedError

    def can_build(self, build_item, data_context):  # check resource requirement
        return False

    def supply_in_progress(self, dc):
        return False


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self):
        super(ZergProductionMgr, self).__init__()

    def reset(self):
        super(ZergProductionMgr, self).reset()

    def update(self, data_context, act_mgr):
        super(ZergProductionMgr, self).update(data_context, act_mgr)
        actions = []
        act_mgr.push_actions(actions)

    def get_goal(self, dc):
        if not self.has_building_built([UNIT_TYPEID.ZERG_LAIR.value,
                                        UNIT_TYPEID.ZERG_HIVE.value]):
            goal = [UNIT_TYPEID.ZERG_LAIR.value] + \
                   [UNIT_TYPEID.ZERG_DRONE.value,
                    UNIT_TYPEID.ZERG_ROACH.value] * 5 + \
                   [UNIT_TYPEID.ZERG_HYDRALISKDEN.value] + \
                   [UNIT_TYPEID.ZERG_ROACH.value,
                    UNIT_TYPEID.ZERG_DRONE.value] * 5
        else:
            num_worker_needed = 0
            bases = dc.dd.base_pool.bases
            for base_tag in bases:
                base = bases[base_tag]
                num_worker_needed += (self.ideal_harvesters(base)
                                      - self.ideal_harvesters(base))
            if num_worker_needed > 0:
                goal = [UNIT_TYPEID.ZERG_DRONE.value,
                        UNIT_TYPEID.ZERG_ROACH.value,
                        UNIT_TYPEID.ZERG_HYDRALISK.value] * num_worker_needed
            else:
                goal = [UNIT_TYPEID.ZERG_ROACH.value] * 2 + \
                       [UNIT_TYPEID.ZERG_HYDRALISK.value] * 3
        return goal

    def perform_search(self, goal):
        return goal

    def get_opening_build_order(self):
        return [UNIT_TYPEID.ZERG_DRONE.value, UNIT_TYPEID.ZERG_DRONE.value,
                UNIT_TYPEID.ZERG_OVERLORD.value, UNIT_TYPEID.ZERG_DRONE.value,
                UNIT_TYPEID.ZERG_DRONE.value,
                UNIT_TYPEID.ZERG_SPAWNINGPOOL.value,
                UNIT_TYPEID.ZERG_EXTRACTOR.value] + \
               [UNIT_TYPEID.ZERG_DRONE.value] * 4 + \
               [UNIT_TYPEID.ZERG_ZERGLING.value,
                UNIT_TYPEID.ZERG_HATCHERY.value] + \
               [UNIT_TYPEID.ZERG_ZERGLING.value,
                UNIT_TYPEID.ZERG_ROACHWARREN.value] + \
               [UNIT_TYPEID.ZERG_DRONE.value, UNIT_TYPEID.ZERG_DRONE.value,
                UNIT_TYPEID.ZERG_ZERGLING.value,
                UNIT_TYPEID.ZERG_EXTRACTOR.value] + \
               [UNIT_TYPEID.ZERG_ROACH.value] * 5

    def should_expand_now(self, dc):
        num = len([unit for unit in self.obs['units']
                   if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_DRONE.value
                   and unit.int_attr.owner == 1])
        bases = dc.dd.base_pool.bases
        ideal_harvesters_all = 0
        base_num = 0
        for base_tag in bases:
            ideal_harvesters_all += self.ideal_harvesters(bases[base_tag])
            if bases[base_tag].unit.float_attr.build_progress == 1:
                base_num += 1
        if (base_num < 2 and num > min(ideal_harvesters_all, 20)
                and not self.building_in_progress(self.base_unit())):
            return True
        if (base_num == 2 and num > min(ideal_harvesters_all, 40)
                and not self.building_in_progress(self.base_unit())):
            return True
        return False

    def can_build(self, build_item, data_context):  # check resource requirement
        if build_item.gasCost > 0:
            extractors = [u for u in self.obs['units']
                          if u.unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value
                          and u.int_attr.owner == 1]
            if len(extractors) == 0:
                self.build_order.queue_as_highest(
                    UNIT_TYPEID.ZERG_EXTRACTOR.value)
                return False
        if not self.has_building_built(build_item.requiredUnits):
            return False
        play_info = self.obs["player"]
        if play_info[3] + build_item.supplyCost > play_info[4]:
            return False
        return (self.obs['player'][1] >= build_item.mineralCost
                and self.obs['player'][2] >= build_item.gasCost)

    def set_build_base(self, build_item, data_context):
        bases = data_context.dd.base_pool.bases
        tag = None
        if build_item.isBuilding:  # build building
            max_num = 0
            for base_tag in bases:
                worker_num = bases[base_tag].unit.int_attr.assigned_harvesters
                if worker_num > max_num:
                    tag = base_tag
                    max_num = worker_num
            if tag:
                if build_item.unit_id == UNIT_TYPEID.ZERG_HATCHERY.value:
                    pos = self.find_base_pos(data_context)
                    if pos is not None:
                        data_context.dd.build_command_queue.put(
                            BuildCmdExpand(base_tag=tag, pos=pos))
#                       data_context.dd.build_command_queue.put(
#                           tag, 1, {'unit_id': build_item.unit_id})
                else:
                    data_context.dd.build_command_queue.put(
                        BuildCmdBuilding(base_tag=tag,
                                         unit_type=build_item.unit_id))
#                    data_context.dd.build_command_queue.put(
#                        tag, 0, {'unit_id': build_item.unit_id})
                return True
        else:  # build unit
            if build_item.unit_id == UNIT_TYPEID.ZERG_DRONE.value:
                max_gap = -200  # find base need worker most
                for base_tag in bases:
                    num_gap = (self.ideal_harvesters(bases[base_tag])
                               - self.assigned_harvesters(bases[base_tag]))
                    if (num_gap > max_gap
                            and len(bases[base_tag].larva_set) > 0):
                        tag = base_tag
                        max_gap = num_gap
            else:
                larva_count = 0  # find base with most larvas
                for base_tag in bases:
                    num_larva = len(bases[base_tag].larva_set)
                    if num_larva > larva_count:
                        tag = base_tag
                        larva_count = num_larva
            if tag:
                data_context.dd.build_command_queue.put(
                    BuildCmdUnit(base_tag=tag, unit_type=build_item.unit_id))
#                data_context.dd.build_command_queue.put(
#                    tag, 0, {'unit_id': build_item.unit_id})
                return True
        return False

    def find_base_pos(self, dc):
        areas = dc.dd.base_pool.resource_cluster
        bases = dc.dd.base_pool.bases
        timestep = dc.sd.timestep
        pathing_grid = timestep.game_info.start_raw.pathing_grid
        array = bitmap2array(pathing_grid)
        dist = {}
        # erase base in pathing_grid
        for tag in bases:
            base = bases[tag].unit
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    array[int(base.float_attr.pos_x) + dx,
                          int(base.float_attr.pos_y) + dy] = 0
        # compute map distance from the base
        for tag in bases:
            base = bases[tag].unit
            dist[tag] = compute_dist(int(base.float_attr.pos_x),
                                     int(base.float_attr.pos_y), array)
        d_min = 10000
        pos = None
        for area in areas:
            d = min([dist[tag][int(area.ideal_base_pos[0]),
                               int(area.ideal_base_pos[1])] for tag in bases])
            if 5 < d < d_min:
                pos = area.ideal_base_pos
                d_min = d
        return pos

    def supply_in_progress(self, dc):
        return any([egg.orders[0].ability_id == ABILITY_ID.TRAIN_OVERLORD.value
                    for egg in dc.dd.base_pool.eggs.values()])

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
