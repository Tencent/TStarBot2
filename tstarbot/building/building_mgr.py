"""Building Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, RACE
from pysc2.lib import TechTree
import random
TT = TechTree()


class BaseBuildingMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass

    def reset(self):
        pass


def dist(unit1, unit2):
    return ((unit1.float_attr.pos_x - unit2.float_attr.pos_x)**2 +
            (unit1.float_attr.pos_y - unit2.float_attr.pos_y)**2)**0.5


def collect_units(units, unit_type, owner=1):
    unit_list = []
    for u in units:
        if u.unit_type == unit_type and u.int_attr.owner == owner:
            unit_list.append(u)
    return unit_list


class ZergBuildingMgr(BaseBuildingMgr):
    def __init__(self):
        super(ZergBuildingMgr, self).__init__()
        self.vespen_status = False

    def reset(self):
        self.vespen_status = False

    def update(self, dc, am):
        super(ZergBuildingMgr, self).update(dc, am)
        self.obs = dc.sd.obs
        units = self.obs['units']
        self.hatcheries = collect_units(units, UNIT_TYPEID.ZERG_LAIR.value) +\
                     collect_units(units, UNIT_TYPEID.ZERG_HATCHERY.value)
        drones = collect_units(units, UNIT_TYPEID.ZERG_DRONE.value)
        self.extractors = collect_units(units, UNIT_TYPEID.ZERG_EXTRACTOR.value)
        self.larvas = collect_units(units, UNIT_TYPEID.ZERG_LARVA.value)
        vespens = collect_units(units, UNIT_TYPEID.NEUTRAL_VESPENEGEYSER.value, 16)
        minerals = collect_units(units, UNIT_TYPEID.NEUTRAL_MINERALFIELD.value, 16) + \
                   collect_units(units, UNIT_TYPEID.NEUTRAL_MINERALFIELD750.value, 16)
        actions = []
        if len(self.hatcheries) > 0:
            self.vespens = [g for g in vespens if dist(g, self.hatcheries[0]) < 15]
            self.minerals = [g for g in minerals if dist(g, self.hatcheries[0]) < 15]

            # TODO: impl here
            if len(self.hatcheries) > 0:
                self.hatchery = self.hatcheries[0]
                cmds = dc.dd.build_command_queue.get(self.hatchery.tag)
                for cmd in cmds:
                    if cmd.cmd_type == 0:  # build
                        unit_type = cmd.param['unit_id']
                        unit_data = TT.getUnitData(unit_type)
                        if unit_data.isBuilding:
                            action = self.produce_building(drones, unit_type)
                        else:
                            action = self.produce_unit(self.larvas, unit_type)
                        actions.extend(action)
        am.push_actions(actions)

    def produce_unit(self, larvas, unit_type):
        if len(larvas) == 0:
            return []
        larva = random.choice(larvas)
        unit_data = TT.getUnitData(unit_type)
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = unit_data.buildAbility
        action.action_raw.unit_command.unit_tags.append(larva.tag)
        return [action]

    def produce_building(self, drones, unit_type, pos_x=None, pos_y=None):
        base_x = self.hatchery.float_attr.pos_x
        base_y = self.hatchery.float_attr.pos_y
        drone = random.choice(drones)
        unit_data = TT.getUnitData(unit_type)
        pos = self.build_place(base_x, base_y, unit_type)
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = unit_data.buildAbility
        if unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value:
            action.action_raw.unit_command.target_unit_tag = self.vespens[0].tag
            for extractor in self.extractors:
                if dist(extractor, self.vespens[0]) < 1:
                    action.action_raw.unit_command.target_unit_tag = self.vespens[1].tag
        elif unit_type != UNIT_TYPEID.ZERG_LAIR.value:
            action.action_raw.unit_command.target_world_space_pos.x = pos[0]
            action.action_raw.unit_command.target_world_space_pos.y = pos[1]
        if unit_type != UNIT_TYPEID.ZERG_LAIR.value:
            action.action_raw.unit_command.unit_tags.append(drone.tag)
        else:
            action.action_raw.unit_command.unit_tags.append(self.hatchery.tag)
        return [action]

    def build_place(self, base_x, base_y, unit_type):
        delta_pos = {UNIT_TYPEID.ZERG_SPAWNINGPOOL.value: [6, 0],
                     UNIT_TYPEID.ZERG_ROACHWARREN.value: [0, -6],
                     UNIT_TYPEID.ZERG_HATCHERY.value: [12, 0],
                     UNIT_TYPEID.ZERG_HYDRALISKDEN.value: [6, -3]}
        if unit_type not in delta_pos:
            return []
        if base_x < base_y:
            pos = [base_x + delta_pos[unit_type][0],
                   base_y + delta_pos[unit_type][1]]
        else:
            pos = [base_x - delta_pos[unit_type][0],
                   base_y - delta_pos[unit_type][1]]
        return pos
