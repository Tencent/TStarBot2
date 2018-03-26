"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import random
import scipy.ndimage as ndimage
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID
from pysc2.lib.features import SCREEN_FEATURES

from pysc2.lib import typeenums as tp
from pysc2.lib import TechTree as TT

class BaseProductionMgr(object):
    def __init__(self, race = tp.RACE.Zerg, use_search = True):
        self.onStart = True
        self.race = race
        self.use_search = use_search

    def reset(self):
        self.onStart = True

    def update(self, obs_mgr, act_mgr):
        ## Get build order given goal
        if self.onStart:
            obs_mgr.BuildOrder.setBuildOrder(self.getOpeningBuildOrder())
            self.onStart = False
        elif obs_mgr.BuildOrder.isEmpty():
            goal = self.get_goal()
            if self.use_search:
                obs_mgr.BuildOrder.setBuildOrder(self.PerformSearch(goal))
            else:
                obs_mgr.BuildOrder.setBuildOrder(goal)

        ## deal with the dead lock if exists (supply, uprade, tech ...)
        if not obs_mgr.BuildOrder.isEmpty():
            while self.DetectDeadlock(obs_mgr):
                pass

    def supply_unit(race):
        if race == tp.RACE.Zerg:
            return tp.UNIT_TYPRID.ZERG_OVERLORD.value
        if race == tp.RACE.Protoss:
            return tp.UNIT_TYPRID.PROTOSS_PYLON.value
        if race == tp.RACE.Terran:
            return tp.UNIT_TYPRID.TERRAN_SUPPLYDEPOT.value
        raise Exception("Race type Error. typeenums.RACE.")

    def DetectDeadLock(self,obs_mgr):
        CurrentItem = obs_mgr.BuildOrder.CurrentItem()
        play_info = obs_mgr.obs.observation["player"]
        if play_info[3] + CurrentItem.supplyCost > play_info[4] and self.supply_unit(self.race) not in obs_mgr.units_in_process:  ## No enough supply and supply not in building process
            obs_mgr.BuildOrder.queueAsHighest(self.supply_unit(self.race))
            return True
        builder = None
        for unit in CurrentItem.whatBuilds:
            if unit in obs_mgr.units_pool or unit in obs_mgr.units_in_process:
                builder = unit
                break
        if builder == None:
            obs_mgr.BuildOrder.queueAsHighest(CurrentItem.whatBuilds[0])
            return True
        requiredUnit = None
        for unit in CurrentItem.requiredUnits or unit in obs_mgr.units_in_process:
            if unit in obs_mgr.units_pool:
                requiredUnit = unit
                break
        if requiredUnit == None:
            obs_mgr.BuildOrder.queueAsHighest(CurrentItem.requiredUnits[0])
            return True
        ## TODO: add Tech upgrade
        #self.set_build_base(CurrentItem, obs_mgr)
        return False

    def getOpeningBuildOrder(self):
        raise NotImplementedError

    def PerformSearch(self, goal):
        return goal

    def set_build_base(self, BuildItem, obs_mgr):
        raise NotImplementedError

    def get_goal(self):
        return []

class ZergProductionLxHanMgr(BaseProductionMgr):
    """ 3 bases + roaches + hydralisk """
    def __init__(self):
        super(ZergProductionLxHanMgr, self).__init__()
        self.drone_limit = 16 + 3 + 3
        self.vespen_status = False

    def reset(self):
        self.vespen_status = False

    def update(self, dc, am):
        super(ZergProductionLxHanMgr, self).update(dc, am)

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
        actions.extend(self.let_idle_drone_collect_mineral(drones, minerals, hatcheries))
        actions.extend(self.produce_drone(larvas, drones))
        actions.extend(self.produce_overlord(larvas, player_info))
        actions.extend(self.build_spawningpool(drones, hatcheries, spawningpool))
        actions.extend(self.build_hatchery(drones, hatcheries, base_pos))
        # actions.extend(self.produce_queen(hatcheries, queen))
        actions.extend(self.build_extractors(drones, extractors, vespens, hatcheries))
        actions.extend(self.let_random_drone_collect_vespen(drones, extractors))
        actions.extend(self.build_roachwarren(drones, hatcheries, roachwarren))
        actions.extend(self.produce_hydralisk(larvas, hydralisk))
        actions.extend(self.produce_roach(larvas))
        actions.extend(self.upgrade_hatchery(hatcheries, base_pos))
        actions.extend(self.build_hydraliskden(drones, hatcheries, hydraliskden))

        am.push_actions(actions)

    def let_idle_drone_collect_mineral(self, drones, minerals, hatcheries):
        actions = []
        for drone in drones:
            if len(drone.orders) == 0:
                action = sc_pb.Action()
                action.action_raw.unit_command.ability_id = ABILITY_ID.HARVEST_GATHER_DRONE.value
                action.action_raw.unit_command.target_unit_tag = self.find_nearest_unit(hatcheries, minerals, 1).tag
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
        action.action_raw.unit_command.unit_tags.append(random.choice(drones).tag)
        actions.append(action)
        return actions

    def build_spawningpool(self, drones, hatcheries, spawningpool):
        actions = []
        if len(spawningpool) != 0:
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

        hatchery = random.choice(hatcheries)
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        if base_x < base_y:  # top left on simple64
            pos = [base_x, base_y - 6]
        else:
            pos = [base_x, base_y + 6]

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
        if len(hydraliskden) != 0:
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
        if N == 1:
            return units[idx[0]]
        for i in range(N):
            selected_units.append(units[idx[i]])
        return selected_units


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self):
        super(ZergProductionMgr, self).__init__()

    def update(self, obs_mgr, act_mgr):
        super(ZergProductionMgr, self).update(obs_mgr, act_mgr)

        actions = []
        # TODO: impl here

        act_mgr.push_actions(actions)

    def PerformSearch(self, goal):
        goal = [UNIT_TYPEID.ZERG_ZERGLING.value]*4
        return goal

    def getOpeningBuildOrder():
        return [UNIT_TYPEID.ZERG_DRONE.value, UNIT_TYPEID.ZERG_DRONE.value, UNIT_TYPEID.ZERG_OVERLORD.value, UNIT_TYPEID.ZERG_SPAWNINGPOOL.value, UNIT_TYPEID.ZERG_DRONE.value] + [UNIT_TYPEID.ZERG_ZERGLING.value]*6


