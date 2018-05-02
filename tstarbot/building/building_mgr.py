"""Building Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from random import choice

import numpy as np
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import ABILITY_ID

from tstarbot.production.production_mgr import BuildCmdUnit
from tstarbot.production.production_mgr import BuildCmdUpgrade
from tstarbot.production.production_mgr import BuildCmdMorph
from tstarbot.production.production_mgr import BuildCmdBuilding
from tstarbot.production.production_mgr import BuildCmdExpand
from tstarbot.production.production_mgr import BuildCmdSpawnLarva
from tstarbot.data.pool.macro_def import WORKER_BUILD_ABILITY


def dist(unit1, unit2):
    """ return Euclidean distance ||unit1 - unit2|| """
    return ((unit1.float_attr.pos_x - unit2.float_attr.pos_x)**2 +
            (unit1.float_attr.pos_y - unit2.float_attr.pos_y)**2)**0.5


def dist_to_pos(unit, x, y):
    """ return Euclidean distance ||unit - [x,y]|| """
    return ((unit.float_attr.pos_x - x)**2 +
            (unit.float_attr.pos_y - y)**2)**0.5


def find_nearest(units, unit):
    """ find the nearest one to 'unit' within the list 'units' """
    if not units:
        return None
    x, y = unit.float_attr.pos_x, unit.float_attr.pos_y
    dd = np.asarray([
        abs(u.float_attr.pos_x - x) + abs(u.float_attr.pos_y - y) for
        u in units])
    return units[dd.argmin()]


def collect_units(units, unit_type, alliance=1):
    """ return unit's ID in the same type """
    return [u for u in units
            if u.unit_type == unit_type and u.int_attr.alliance == alliance]


def is_building(unit):
    """  """
    if unit.orders:
        return unit.orders[0].ability_id in WORKER_BUILD_ABILITY
    return False


def act_build_by_self(builder_tag, ability_id):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ability_id
    action.action_raw.unit_command.unit_tags.append(builder_tag)
    return action


def act_build_by_tag(builder_tag, target_tag, ability_id):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ability_id
    action.action_raw.unit_command.target_unit_tag = target_tag
    action.action_raw.unit_command.unit_tags.append(builder_tag)
    return action


def act_build_by_pos(builder_tag, target_pos, ability_id):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ability_id
    action.action_raw.unit_command.target_world_space_pos.x = target_pos[0]
    action.action_raw.unit_command.target_world_space_pos.y = target_pos[1]
    action.action_raw.unit_command.unit_tags.append(builder_tag)
    return action


class BaseBuildingMgr(object):
    def __init__(self, dc):
        pass

    def update(self, dc, am):
        pass

    def reset(self):
        pass


class ZergBuildingMgr(BaseBuildingMgr):
    def __init__(self, dc):
        super(ZergBuildingMgr, self).__init__(dc)
        self.verbose = 0
        self._step = 0
        self.TT = dc.sd.TT  # tech tree
        self._init_config(dc)  # do it last, as it overwrites previous members

    def reset(self):
        self._step = 0

    def update(self, dc, am):
        super(ZergBuildingMgr, self).update(dc, am)

        if self.verbose >= 2:
            units = dc.sd.obs['units']
            all_larva = collect_units(units, UNIT_TYPEID.ZERG_LARVA.value)
            all_queen = collect_units(units, UNIT_TYPEID.ZERG_QUEEN.value)
            print('ZergBuildingMgr: step = {}'.format(self._step))
            print('len commands = {}'.format(dc.dd.build_command_queue.size()))
            print('len queen = {}'.format(len(all_queen)))
            print('len larva = {}'.format(len(all_larva)))

        self._step += 1

        if dc.dd.build_command_queue.empty():
            return

        accepted_cmds = [
            BuildCmdUnit,
            BuildCmdUpgrade,
            BuildCmdMorph,
            BuildCmdBuilding,
            BuildCmdExpand,
            BuildCmdSpawnLarva
        ]
        actions = []
        for _ in range(dc.dd.build_command_queue.size()):
            cmd = dc.dd.build_command_queue.get()
            if type(cmd) not in accepted_cmds:
                # put back unknown command
                dc.dd.build_command_queue.put(cmd)
                continue
            action = None
            if type(cmd) == BuildCmdUnit:
                action = self._build_unit(cmd, dc)
            elif type(cmd) == BuildCmdUpgrade:
                action = self._build_upgrade_tech(cmd, dc)
            elif type(cmd) == BuildCmdMorph:
                action = self._build_morph(cmd, dc)
            elif type(cmd) == BuildCmdBuilding:
                action = self._build_building(cmd, dc)
            elif type(cmd) == BuildCmdExpand:
                action = self._build_base_expand(cmd, dc)
            elif type(cmd) == BuildCmdSpawnLarva:
                action = self._spawn_larva(cmd, dc)
            if action:
                actions.append(action)
        am.push_actions(actions)

    def _init_config(self, dc):
        if hasattr(dc, 'config'):
            if hasattr(dc.config, 'building_verbose'):
                self.verbose = dc.config.building_verbose

    def _build_unit(self, cmd, dc):
        base_instance = dc.dd.base_pool.bases[cmd.base_tag]
        if not base_instance:
            if self.verbose >= 1:
                print(
                    "Warning: ZergBuildingMgr._build_unit: "
                    "base_tag {} invalid in base_pool".format(cmd.base_tag)
                )
            return None
        ability_id = self.TT.getUnitData(cmd.unit_type).buildAbility
        if cmd.unit_type == UNIT_TYPEID.ZERG_QUEEN.value:
            return act_build_by_self(builder_tag=cmd.base_tag,
                                     ability_id=ability_id)
        else:
            if not base_instance.larva_set:
                if self.verbose >= 1:
                    print("Warning: ZergBuildingMgr._build_unit: "
                          "empty larva set".format(cmd.base_tag))
                return None
            larva_tag = choice(list(base_instance.larva_set))
            return act_build_by_self(builder_tag=larva_tag,
                                     ability_id=ability_id)

    def _build_upgrade_tech(self, cmd, dc):
        builder_tag = cmd.building_tag
        ability_id = cmd.ability_id
        return act_build_by_self(builder_tag, ability_id)

    def _build_morph(self, cmd, dc):
        builder_tag = cmd.unit_tag
        ability_id = cmd.ability_id
        if self.verbose >= 1:
            if ability_id == ABILITY_ID.MORPH_LURKERDEN.value:
                print('building MORPH_LURKERDEN')
            if ability_id == ABILITY_ID.MORPH_LURKER.value:
                print('morphing lurker')
            if ability_id == ABILITY_ID.MORPH_GREATERSPIRE.value:
                print('morphing greater spire')
            if ability_id == ABILITY_ID.MORPH_BROODLORD.value:
                print('morphing broodlord')
        return act_build_by_self(builder_tag, ability_id)

    def _build_building(self, cmd, dc):
        unit_type = cmd.unit_type
        ability_id = self.TT.getUnitData(unit_type).buildAbility

        builder_tag, target_tag = self._can_build_by_tag(cmd, dc)
        if builder_tag and target_tag:
            return act_build_by_tag(
                builder_tag, target_tag, ability_id)

        builder_tag, target_pos = self._can_build_by_pos(cmd, dc)
        if builder_tag and target_pos:
            return act_build_by_pos(
                builder_tag, target_pos, ability_id)

        # TODO: use logger
        if self.verbose >= 1:
            print(
                "Warning: ZergBuildingMgr._build_building: "
                "cannot handle building command {}".format(cmd)
            )
        return None

    def _can_build_by_tag(self, cmd, dc):
        builder_tag, target_tag = None, None
        unit_type = cmd.unit_type
        if unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value:
            base_instance = dc.dd.base_pool.bases[cmd.base_tag]
            if base_instance:
                builder_tag = self._find_available_worker_for_building(
                    dc, base_instance)
                target_tag = self._find_available_gas(dc, base_instance)
        return builder_tag, target_tag

    def _can_build_by_pos(self, cmd, dc):
        # use pre defined relative position
        delta_pos = {
            UNIT_TYPEID.ZERG_SPAWNINGPOOL.value: [6, 0],
            UNIT_TYPEID.ZERG_ROACHWARREN.value: [0, -6],
            UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value: [-3, -8],
            UNIT_TYPEID.ZERG_HYDRALISKDEN.value: [6, -3],
            UNIT_TYPEID.ZERG_SPIRE.value: [3, -6],
            UNIT_TYPEID.ZERG_LURKERDENMP.value: [7, -7],
            UNIT_TYPEID.ZERG_INFESTATIONPIT.value: [1, -9]
        }

        builder_tag, target_pos = None, ()
        unit_type = cmd.unit_type
        if hasattr(cmd, 'base_tag') and unit_type in delta_pos:
            if self.verbose >= 1:
                print('building {}'.format(unit_type))
                if unit_type == UNIT_TYPEID.ZERG_LURKERDENMP.value:
                    print('building LURKERDENMP')

            base_instance = dc.dd.base_pool.bases[cmd.base_tag]

            builder_tag = self._find_available_worker_for_building(
                dc, base_instance)

            base_x = base_instance.unit.float_attr.pos_x
            base_y = base_instance.unit.float_attr.pos_y
            if base_x < base_y:
                target_pos = [base_x + delta_pos[unit_type][0],
                              base_y + delta_pos[unit_type][1]]
            else:
                target_pos = [base_x - delta_pos[unit_type][0],
                              base_y - delta_pos[unit_type][1]]
        return builder_tag, target_pos

    def _build_base_expand(self, cmd, dc):
        base_instance = dc.dd.base_pool.bases[cmd.base_tag]
        if base_instance:
            builder_tag = self._find_available_worker_for_building(
                dc, base_instance)
            if builder_tag:
                target_pos = cmd.pos
                ability_id = ABILITY_ID.BUILD_HATCHERY.value
                return act_build_by_pos(builder_tag, target_pos, ability_id)
        if self.verbose >= 1:
            print(
                "Warning: ZergBuildingMgr._build_base_expand: "
                "invalid base_tag in base_pool or no worker around this base"
            )
        return None

    def _find_available_worker_for_building(self, dc, base_instance):
        # find a worker, which must be not building, for the building task
        # the found worker can be idle, harvesting mineral/gas, etc.
        for w_tag in base_instance.worker_set:
            w_unit = dc.dd.worker_pool.get_by_tag(w_tag).unit
            if w_unit and not is_building(w_unit):
                return w_tag
        return None

    def _find_available_gas(self, dc, base_instance):
        # find a vacant vespene/gas on which there is NO extractor
        for gas_tag in base_instance.gas_set:
            gas_unit = dc.dd.base_pool.vespenes[gas_tag]
            vb_units = [v for _, v in dc.dd.base_pool.vbs.items()]
            vb_unit = find_nearest(vb_units, gas_unit)
            if not vb_unit:
                # not a single extractor at all; this gas must be vacant
                return gas_tag
            dx = vb_unit.float_attr.pos_x - gas_unit.float_attr.pos_x
            dy = vb_unit.float_attr.pos_y - gas_unit.float_attr.pos_y
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                return gas_tag
        return None

    def _spawn_larva(self, cmd, dc):
        # queen injects larva on a base
        builder_tag = cmd.queen_tag
        target_tag = cmd.base_tag
        ability_id = ABILITY_ID.EFFECT_INJECTLARVA.value
        return act_build_by_tag(builder_tag, target_tag, ability_id)
