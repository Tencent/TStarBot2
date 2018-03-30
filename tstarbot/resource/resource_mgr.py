"""Resource Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import random
from copy import deepcopy

from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, RACE


def collect_units(units, unit_type, owner=1):
    unit_list = []
    for u in units:
        if u.unit_type == unit_type and u.int_attr.owner == owner:
            unit_list.append(u)
    return unit_list


def collect_tags(units):
    return [u.tag for u in units]


def find_by_tag(units, tag):
    for u in units:
        if u.tag == tag:
            return u
    return None


def get_target_tag(unit, idx=0):
    if len(unit.orders)>0:
        return unit.orders[idx].target_tag
    return None


def print_harvester(units, name=''):
    print('len {} = '.format(name), len(units))
    for u in units:
        print('type = ', u.int_attr.unit_type,
              'ideal_harvesters = ', u.int_attr.ideal_harvesters,
              'assigned_harvesters = ', u.int_attr.assigned_harvesters)


def act_worker_harvests_on_target(target_tag, worker_tag):
    # The CALLER should assure the target-worker is a reasonable pair
    # e.g., the target is an extractor, a mineral,
    # the worker should not be too far away to the target
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
        ABILITY_ID.HARVEST_GATHER_DRONE.value
    action.action_raw.unit_command.target_unit_tag = target_tag
    action.action_raw.unit_command.unit_tags.append(worker_tag)
    return action


class BaseResourceMgr(object):
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass

    def reset(self):
        pass


class DancingDronesResourceMgr(BaseResourceMgr):
    def __init__(self):
        super(DancingDronesResourceMgr, self).__init__()
        self._range_high = 5
        self._range_low = -5
        self._move_ability = 1

    def update(self, dc, am):
        super(DancingDronesResourceMgr, self).update(dc, am)

        drone_ids = dc.get_drones()
        pos = dc.get_hatcherys()

        print('pos=', pos)
        actions = self.move_drone_random_round_hatchery(drone_ids, pos[0])

        am.push_actions(actions)

    def move_drone_random_round_hatchery(self, drone_ids, pos):
        length = len(drone_ids)
        actions = []
        for drone in drone_ids:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = self._move_ability
            x = pos[0] + random.randint(self._range_low, self._range_high)
            y = pos[1] + random.randint(self._range_low, self._range_high)
            action.action_raw.unit_command.target_world_space_pos.x = x
            action.action_raw.unit_command.target_world_space_pos.y = y
            action.action_raw.unit_command.unit_tags.append(drone)
            actions.append(action)
        return actions


class BaseTerritoryMgr(object):
    class Territory(object):
        def __init__(self):
            is_capital = False
            nearest_mineral_tag = None

    def __init__(self):
        self.base_to_territory = {}
        pass

    def reset(self):
        pass

    def update(self, all_bases, all_minerals):
        pass


class ZergResourceMgr(BaseResourceMgr):
    def __init__(self):
        super(ZergResourceMgr, self).__init__()

        self.update_base_territory_freq = 30

        self.bt_mgr = BaseTerritoryMgr()
        self.all_bases = None
        self.all_extractors = None
        self.all_workers = None
        self.step = 0

    def reset(self):
        self.bt_mgr.reset()
        self.all_bases = None
        self.all_extractors = None
        self.all_workers = None
        self.step = 0

    def update(self, dc, am):
        super(ZergResourceMgr, self).update(dc, am)

        units = dc.sd.obs['units']

        self.all_bases = collect_units(units, UNIT_TYPEID.ZERG_HATCHERY.value) \
            + collect_units(units, UNIT_TYPEID.ZERG_LAIR.value)
        self.all_extractors = collect_units(units,
                                            UNIT_TYPEID.ZERG_EXTRACTOR.value)
        self.all_workers = collect_units(units, UNIT_TYPEID.ZERG_DRONE.value)

        # print_harvester(self.all_bases, name='all_basese')
        # print_harvester(self.all_extractors, name='all_extractors')
        # print('len workers = ', len(self.all_workers))

        actions = []
        actions += self._update_harvest_gas()
        actions += self._update_harvest_mineral()

        am.push_actions(actions)
        self.step += 1

    def _update_harvest_gas(self):
        actions = []

        for e in self.all_extractors:
            n_remain = e.int_attr.ideal_harvesters - \
                       e.int_attr.assigned_harvesters
            if n_remain <= 0:
                continue
            workers = self._find_available_workers_for_gas(n_remain)
            for w in workers:
                actions += [act_worker_harvests_on_target(target_tag=e.tag,
                                                          worker_tag=w.tag)]

        return actions

    def _update_harvest_mineral(self):
        actions = []

        for b in self.all_bases:
            n_remain = b.int_attr.ideal_harvesters - \
                       b.int_attr.assigned_harvesters
            if n_remain <= 0:
                # ideal_harvesters seems a suggested number provided by the game
                #  core, if the base is not near a mineral cluster, this number
                # is zero! Is it true?
                # TODO: add STOP logic when over-filled?
                continue
            w = self._find_available_workers_for_mineral(1)  # find only ONE
            if w:
                # let the worker harvest the base, not the mineral.
                # Does it always work??
                actions += [act_worker_harvests_on_target(target_tag=b.tag,
                                                          worker_tag=w[0].tag)]

        return actions

    def _find_available_workers_for_gas(self, num=1):
        ww = []
        for w in self.all_workers:
            if len(ww) >= num:
                break
            target_tag = get_target_tag(w)
            if not target_tag or not find_by_tag(units=self.all_extractors,
                                                 tag=target_tag):
                # this worker has no target or is not working on any extractor
                ww.append(w)
        return ww

    def _find_available_workers_for_mineral(self, num=1):
        ww = []
        for w in self.all_workers:
            if len(ww) >= num:
                break
            target_tag = get_target_tag(w)
            if not target_tag:  # this is an idle worker
                ww.append(w)
        return ww
