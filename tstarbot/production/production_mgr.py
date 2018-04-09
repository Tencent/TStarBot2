"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import random
import scipy.ndimage as ndimage
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, RACE
from pysc2.lib.features import SCREEN_FEATURES
from pysc2.lib import TechTree
from collections import deque, namedtuple

TT = TechTree()

BuildCmdBuilding = namedtuple('build_cmd_building', ['base_tag', 'unit_type'])
BuildCmdUnit = namedtuple('build_cmd_unit', ['base_tag', 'unit_type'])
BuildCmdExpand = namedtuple('build_cmd_expand', ['base_tag', 'pos'])
BuildCmdHarvest = namedtuple('build_cmd_harvest', ['gas_first'])  # binary indictor


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
        self.supply_cap = None
        self.supply_in_progress = False

    def reset(self):
        self.onStart = True
        self.build_order.clear_all()
        self.obs = None
        self.supply_cap = None
        self.supply_in_progress = False

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

        self.check_supply()

        # check resource, larva, builder requirement and determine the build base
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
        play_info = self.obs["player"]
        builder = None
        for unit_id in current_item.whatBuilds:
            # if unit_id in data_contxt.units_pool or unit in data_context.units_in_process:
            if unit_id == UNIT_TYPEID.ZERG_LARVA.value or self.has_unit(
                    self.obs["units"], unit_id):
                builder = unit_id
                break
        if builder is None and len(current_item.whatBuilds) > 0:
            self.build_order.queue_as_highest(current_item.whatBuilds[0])
            return True
        required_unit = None
        for unit_id in current_item.requiredUnits:
            # if unit_id in data_context.units_pool or unit_id in data_context.units_in_process:
            if self.has_unit(self.obs["units"], unit_id):
                required_unit = unit_id
                break
        if required_unit is None and len(current_item.requiredUnits) > 0:
            self.build_order.queue_as_highest(current_item.requiredUnits[0])
            return True
        # TODO: add Tech upgrade
        return False

    def check_supply(self):
        play_info = self.obs["player"]
        current_item = self.build_order.current_item()
        if play_info[4] != self.supply_cap:
            self.supply_in_progress = False
            self.supply_cap = play_info[4]
        # No enough supply and supply not in building process
        if (play_info[3] + current_item.supplyCost >
                    play_info[4] - min(6, max(0, (play_info[4]-30)/10))
                and not self.supply_in_progress
                and current_item.unit_id != self.supply_unit()):
            self.build_order.queue_as_highest(self.supply_unit())

    def has_unit(self, units, unit_id, owner=1):
        for unit in units:
            if unit.unit_type == unit_id and unit.int_attr.owner == owner:
                return True
        return False

    def has_building_built(self, units, unit_id_list, owner=1):
        for unit_id in unit_id_list:
            for unit in units:
                if unit.unit_type == unit_id and unit.int_attr.owner == owner and unit.float_attr.build_progress == 1:
                    return True
        return len(unit_id_list) == 0

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


class ZergProductionLxHanMgr(object):
    """ 3 bases + roaches + hydralisk """

    def __init__(self):
        super(ZergProductionLxHanMgr, self).__init__()
        self.drone_limit = 16 + 3 + 3
        self.vespen_status = False

    def reset(self):
        self.vespen_status = False

    def update(self, dc, am):

        screen = dc.screen
        player_info = dc.player_info
        base_pos = dc.base_pos

        drones = dc.get_drones()
        minerals = dc.get_minerals()
        hatcheries = dc.get_hatcheries()
        larvas = dc.get_larvas()
        queen = dc.get_queen()
        spawningpool = dc.get_spawningpool()
        extractors = dc.get_extractor()
        vespens = dc.get_vespens()
        roachwarren = dc.get_roachwarren()
        hydraliskden = dc.get_hydraliskden()
        hydralisk = dc.get_hydralisk()

        if len(roachwarren) > 0 and player_info[2] == 0:
            self.vespen_status = False
        if len(roachwarren) > 0 and player_info[2] > 0:
            self.vespen_status = True

        actions = []
        # actions.extend(self.set_default_rally_drone(drones, hatcheries))
        actions.extend(
            self.let_idle_drone_collect_mineral(drones, minerals, hatcheries))
        actions.extend(self.produce_drone(larvas, drones))
        actions.extend(self.produce_overlord(larvas, player_info))
        actions.extend(
            self.build_spawningpool(drones, hatcheries, spawningpool))
        actions.extend(self.build_hatchery(drones, hatcheries, base_pos))
        # actions.extend(self.produce_queen(hatcheries, queen))
        actions.extend(
            self.build_extractors(drones, extractors, vespens, hatcheries))
        actions.extend(self.let_random_drone_collect_vespen(drones, extractors))
        actions.extend(self.build_roachwarren(drones, hatcheries, roachwarren))
        actions.extend(self.produce_hydralisk(larvas, hydralisk))
        actions.extend(self.produce_roach(larvas))
        actions.extend(self.upgrade_hatchery(hatcheries, base_pos))
        actions.extend(
            self.build_hydraliskden(drones, hatcheries, hydraliskden))

        am.push_actions(actions)

    def let_idle_drone_collect_mineral(self, drones, minerals, hatcheries):
        actions = []
        for drone in drones:
            if len(drone.orders) == 0:
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = ABILITY_ID.HARVEST_GATHER_DRONE.value
                mine = self.find_nearest_unit(hatcheries, minerals, 1)
                if len(mine) == 0:
                    return []
                action.action_raw.unit_command.target_unit_tag = mine[0].tag
                action.action_raw.unit_command.unit_tags.append(drone.tag)
                actions.append(action)
        return actions

    def let_random_drone_collect_vespen(self, drones, extractors):
        actions = []
        if len(extractors) < 2 or self.vespen_status:
            return actions
        for e in extractors:
            for i in range(3):
                drone = random.choice(drones)
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = ABILITY_ID.HARVEST_GATHER_DRONE.value
                action.action_raw.unit_command.target_unit_tag = e.tag
                action.action_raw.unit_command.unit_tags.append(drone.tag)
                actions.append(action)
        self.vespen_status = True
        return actions

    def set_default_rally_drone(self, hatcheries, minerals):
        actions = []
        for hatchery in hatcheries:
            if hatchery.orders[0].ability_id != ABILITY_ID.RALLY_HATCHERY_WORKERS:
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = ABILITY_ID.RALLY_HATCHERY_WORKERS.value
                action.action_raw.unit_command.target_unit_tag = minerals[0].tag
                action.action_raw.unit_command.unit_tags.append(hatchery.tag)
                actions.append(action)
        return actions

    def produce_drone(self, larvas, drones):
        actions = []
        for larva in larvas:
            if len(drones) < self.drone_limit:
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = ABILITY_ID.TRAIN_DRONE.value
                action.action_raw.unit_command.unit_tags.append(larva.tag)
                actions.append(action)
        return actions

    def produce_overlord(self, larvas, player_info):
        actions = []
        if player_info[4] >= 200:
            return actions
        if player_info[4] - player_info[3] <= 2:
            if len(larvas) == 0:
                return []
            larva = random.choice(larvas)
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.TRAIN_OVERLORD.value
            action.action_raw.unit_command.unit_tags.append(larva.tag)
            actions.append(action)
        return actions

    def produce_queen(self, hatcheries, queen):
        actions = []
        if len(queen) > 0:
            return actions
        for hatchery in hatcheries:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.TRAIN_QUEEN.value
            action.action_raw.unit_command.unit_tags.append(hatchery.tag)
            actions.append(action)
        return actions

    def produce_roach(self, larvas):
        actions = []
        for larva in larvas:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.TRAIN_ROACH.value
            action.action_raw.unit_command.unit_tags.append(larva.tag)
            actions.append(action)
        return actions

    def produce_hydralisk(self, larvas, hydralisk):
        actions = []
        if len(hydralisk) >= 10:
            return actions
        for larva in larvas:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.TRAIN_HYDRALISK.value
            action.action_raw.unit_command.unit_tags.append(larva.tag)
            actions.append(action)
        return actions

    def build_hatchery(self, drones, hatcheries, base_pos):
        actions = []
        if len(drones) == 0:
            return []
        if len(hatcheries) > 3:
            return actions

        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BUILD_HATCHERY.value

        base_x = base_pos[0]
        base_y = base_pos[1]

        pos_list = []
        if base_x < base_y:  # top left on simple64
            pos = [base_x + 12, base_y]
            pos_list.append(pos)
            pos = [base_x + 12, base_y + 6]
            pos_list.append(pos)
        else:
            pos = [base_x - 12, base_y]
            pos_list.append(pos)
            pos = [base_x - 12, base_y - 6]
            pos_list.append(pos)

        if len(pos_list) == 0:
            return []

        pos = random.choice(pos_list)

        action.action_raw.unit_command.target_world_space_pos.x = pos[0]
        action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        action.action_raw.unit_command.unit_tags.append(
            random.choice(drones).tag)
        actions.append(action)
        return actions

    def build_spawningpool(self, drones, hatcheries, spawningpool):
        actions = []
        if len(spawningpool) != 0:
            return actions

        if len(hatcheries) == 0:
            return actions
        hatchery = random.choice(hatcheries)
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        if base_x < base_y:  # top left on simple64
            pos = [base_x + 6, base_y]
        else:
            pos = [base_x - 6, base_y]

        drone = random.choice(drones)
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BUILD_SPAWNINGPOOL.value
        action.action_raw.unit_command.target_world_space_pos.x = pos[0]
        action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        action.action_raw.unit_command.unit_tags.append(drone.tag)
        actions.append(action)

        return actions

    def build_extractors(self, drones, extractors, vespens, hatcheries):
        actions = []
        if len(extractors) >= 2:
            return actions

        vespens = self.find_nearest_unit(hatcheries, vespens, 2)
        if len(vespens) == 0:
            return []
        for i in [0, 1]:
            drone = random.choice(drones)
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.BUILD_EXTRACTOR.value
            action.action_raw.unit_command.target_unit_tag = vespens[i].tag
            action.action_raw.unit_command.unit_tags.append(drone.tag)
            actions.append(action)

        return actions

    def build_roachwarren(self, drones, hatcheries, roachwarren):
        actions = []
        if len(roachwarren) != 0:
            return actions

        if len(hatcheries) == 0:
            return actions
        hatchery = random.choice(hatcheries)
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        if base_x < base_y:  # top left on simple64
            pos = [base_x, base_y - 6]
        else:
            pos = [base_x, base_y + 6]

        if len(drones) == 0:
            return []
        drone = random.choice(drones)
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BUILD_ROACHWARREN.value
        action.action_raw.unit_command.target_world_space_pos.x = pos[0]
        action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        action.action_raw.unit_command.unit_tags.append(drone.tag)
        actions.append(action)

        return actions

    def build_hydraliskden(self, drones, hatcheries, hydraliskden):
        actions = []
        if len(drones) == 0:
            return []
        if len(hydraliskden) != 0:
            return actions

        if len(hatcheries) == 0:
            return actions
        hatchery = random.choice(hatcheries)
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        if base_x < base_y:  # top left on simple64
            pos = [base_x + 6, base_y - 2]
        else:
            pos = [base_x - 6, base_y + 2]

        drone = random.choice(drones)
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BUILD_HYDRALISKDEN.value
        action.action_raw.unit_command.target_world_space_pos.x = pos[0]
        action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        action.action_raw.unit_command.unit_tags.append(drone.tag)
        actions.append(action)

        return actions

    def upgrade_hatchery(self, hatcheries, base_pos):
        actions = []
        base_h = []
        for hatchery in hatcheries:
            if hatchery.float_attr.pos_x == base_pos[0]:
                base_h = hatchery
                break
        if len(base_h) == 0:
            return []
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.MORPH_LAIR.value
        action.action_raw.unit_command.unit_tags.append(base_h.tag)
        actions.append(action)
        return actions

    def find_vacant_creep_location(self, screen, erosion_size):
        unit_type = screen[SCREEN_FEATURES.unit_type.index]
        creep = screen[SCREEN_FEATURES.creep.index]
        vacant = (unit_type == 0) & (creep == 1)
        vacant_erosed = ndimage.grey_erosion(
            vacant, size=(erosion_size, erosion_size))
        candidate_xy = np.transpose(np.nonzero(vacant_erosed)).tolist()
        if len(candidate_xy) == 0:
            return None
        return random.choice(candidate_xy)

    def find_nearest_unit(self, hatcheries, units, N):
        if len(hatcheries) == 0:
            return []
        hatchery = random.choice(hatcheries)
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        dists = []
        for m in units:
            x = m.float_attr.pos_x
            y = m.float_attr.pos_y
            dist = abs(x - base_x) + abs(y - base_y)
            dists.append(dist)
        idx = np.argsort(dists)
        selected_units = []
        for i in range(N):
            selected_units.append(units[idx[i]])
        return selected_units


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self):
        super(ZergProductionMgr, self).__init__()

    def reset(self):
        super(ZergProductionMgr, self).reset()

    def update(self, data_context, act_mgr):
        super(ZergProductionMgr, self).update(data_context, act_mgr)
        actions = []
        # TODO: impl here
        act_mgr.push_actions(actions)

    def get_goal(self, dc):
        if not self.has_building_built(self.obs['units'],
                   [UNIT_TYPEID.ZERG_LAIR.value, UNIT_TYPEID.ZERG_HIVE.value]):
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
                base = bases[base_tag].unit
                num_worker_needed += base.int_attr.ideal_harvesters \
                                     - base.int_attr.assigned_harvesters
            if num_worker_needed > 0:
                goal = [UNIT_TYPEID.ZERG_DRONE.value,
                        UNIT_TYPEID.ZERG_ROACH.value,
                        UNIT_TYPEID.ZERG_HYDRALISK.value] * num_worker_needed
            else:
                goal = [UNIT_TYPEID.ZERG_ROACH.value] * 2 + [UNIT_TYPEID.ZERG_HYDRALISK.value] * 3
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

    def should_expand_now(self, data_contex):
        return False

    def can_build(self, build_item, data_context):  # check resource requirement
        if self.obs['player'][2] < build_item.gasCost:
            extractors = [u for u in self.obs['units']
                          if u.unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value
                          and u.int_attr.owner == 1]
            if len(extractors) == 0:
                self.build_order.queue_as_highest(
                    UNIT_TYPEID.ZERG_EXTRACTOR.value)
                return False
        if not self.has_building_built(self.obs['units'],
                                       build_item.requiredUnits):
            return False
        play_info = self.obs["player"]
        if play_info[3] + build_item.supplyCost > play_info[4]:
            return False
        return self.obs['player'][1] >= build_item.mineralCost \
               and self.obs['player'][2] >= build_item.gasCost

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
                    data_context.dd.build_command_queue.put(
                        BuildCmdExpand(base_tag=tag, pos=pos))
                    #data_context.dd.build_command_queue.put(
                    #    tag, 1, {'unit_id': build_item.unit_id})
                else:
                    data_context.dd.build_command_queue.put(
                        BuildCmdBuilding(base_tag=tag, unit_type=build_item.unit_id))
                    #data_context.dd.build_command_queue.put(
                    #    tag, 0, {'unit_id': build_item.unit_id})
                return True
        else:  # build unit
            if build_item.unit_id == UNIT_TYPEID.ZERG_DRONE.value:
                max_gap = -200  # find base need worker most
                for base_tag in bases:
                    num_gap = (self.ideal_harvesters_all(bases[base_tag])
                               - self.assigned_harvesters_all(bases[base_tag]))
                    if (num_gap > max_gap and
                                len(bases[base_tag].larva_set) > 0):
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
                #data_context.dd.build_command_queue.put(
                #    tag, 0, {'unit_id': build_item.unit_id})
                if build_item.unit_id == UNIT_TYPEID.ZERG_OVERLORD.value:
                    self.supply_in_progress = True
                return True
        return False

    def find_base_pos(self, dc):
        areas = dc.dd.base_pool.resource_cluster
        bases = dc.dd.base_pool.bases
        d_min = 10000
        pos = None
        for area in areas:
            d = min([dist_to_pos(bases[tag].unit, area.ideal_base_pos)
                 for tag in bases])
            if d < d_min and d > 5:
                pos = area.ideal_base_pos
                d_min = d
        return pos

    def find_unit_by_tag(self, units, tag):
        return [unit for unit in units if unit.tag==tag]

    def ideal_harvesters_all(self, base_item):
        num = base_item.unit.int_attr.ideal_harvesters
        for vb_tag in base_item.vb_set:
            vb = self.find_unit_by_tag(self.obs['units'], vb_tag)[0]
            num += vb.int_attr.ideal_harvesters
        return num

    def assigned_harvesters_all(self, base_item):
        num = base_item.unit.int_attr.assigned_harvesters
        for vb_tag in base_item.vb_set:
            vb = self.find_unit_by_tag(self.obs['units'], vb_tag)[0]
            num += vb.int_attr.assigned_harvesters
        return num
