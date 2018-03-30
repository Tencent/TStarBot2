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


class ExtractorWorkerTagMgrOld(object):
    """ Maintain the Extractor-Worker bi-directional mapping/contract using tags """
    MAX_WORKERS_PER_EXTRACTOR = 3

    def __init__(self):
        self.extractor_to_workers = {}

    def reset(self):
        self.extractor_to_workers = {}

    def update(self, all_extractor_tags, all_worker_tags):
        self._add_extractor_if_has_new(all_extractor_tags)
        self._remove_extractor_if_not_exist(all_extractor_tags)
        self._remove_workers_if_not_exist(all_worker_tags)

    def _add_extractor_if_has_new(self, all_extractor_tags):
        for e in all_extractor_tags:
            if not self.extractor_to_workers.get(e, False):
                self.extractor_to_workers[e] = []

    def _remove_extractor_if_not_exist(self, all_extractor_tags):
        for e in self.extractor_to_workers:
            if e not in all_extractor_tags:
                self.extractor_to_workers.pop(e, None)

    def _remove_workers_if_not_exist(self, all_worker_tags):
        for _, worker_tags in self.extractor_to_workers.items():
            for w_tag in worker_tags:
                if w_tag not in all_worker_tags:
                    worker_tags.remove(w_tag)  # this should affect self.extractor_to_workers[e] due to the by-ref semantics

    def act_worker_harvests_on_extractor(self, extractor_tag, worker_tag):
        # REMEMBER to update the mapping!
        # The CALLER should assure the extractor-worker is a reasonable pair
        self.extractor_to_workers[extractor_tag].append(worker_tag)

        # make the real action
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.HARVEST_GATHER_DRONE.value
        action.action_raw.unit_command.target_unit_tag = extractor_tag
        action.action_raw.unit_command.unit_tags.append(worker_tag)
        return [action]

    def contain_worker(self, worker_tag):
        for _, workers in self.extractor_to_workers.items():
            if worker_tag in workers:
                return True
        return False


class ExtractorWorkerTagMgr(object):
    """ Maintain the Extractor-Worker bi-directional mapping/contract using tags """
    MAX_WORKERS_PER_EXTRACTOR = 3

    def __init__(self):
        self.extractor_tag_to_workers_num = {}

    def reset(self):
        self.extractor_tag_to_workers_num = {}

    def update(self, all_extractor, all_worker):
        self._add_extractor_if_has_new(all_extractor)
        self._remove_extractor_if_not_exist(all_extractor)
        self._update_num_workers(all_worker)

    def _add_extractor_if_has_new(self, all_extractor):
        for e in all_extractor:
            if not self.extractor_tag_to_workers_num.get(e.tag, False):
                self.extractor_tag_to_workers_num[e.tag] = 0

    def _remove_extractor_if_not_exist(self, all_extractor):
        for e_tag in self.extractor_tag_to_workers_num:
            if not find_by_tag(all_extractor, e_tag):
                self.extractor_tag_to_workers_num.pop(e_tag, None)

    def _update_num_workers(self, all_workers):
        for w in all_workers:
            target_tag = get_target_tag(w)
            if target_tag and target_tag in self.extractor_tag_to_workers_num:
                self.extractor_tag_to_workers_num[target_tag] += 1

    def act_worker_harvests_on_extractor(self, extractor_tag, worker_tag):
        # REMEMBER to update the mapping!
        # The CALLER should assure the extractor-worker is a reasonable pair
        self.extractor_tag_to_workers_num[extractor_tag] += 1

        # make the real action
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.HARVEST_GATHER_DRONE.value
        action.action_raw.unit_command.target_unit_tag = extractor_tag
        action.action_raw.unit_command.unit_tags.append(worker_tag)
        return [action]


class ZergResourceMgr(BaseResourceMgr):
    def __init__(self):
        super(ZergResourceMgr, self).__init__()

        self.update_harvest_gas_freq = 6
        self.update_harvest_mineral_freq = 6

        self.step = 0
        self.ew_mgr = ExtractorWorkerTagMgr()
        self.tmp = set([])

    def reset(self):
        self.step = 0
        self.ew_mgr.reset()

    def update(self, dc, am):
        super(ZergResourceMgr, self).update(dc, am)

        units = dc.sd.obs['units']

        all_extractors = collect_units(units, UNIT_TYPEID.ZERG_EXTRACTOR.value)
        #all_extractor_tags = collect_tags(all_extractors)
        all_workers = collect_units(units, UNIT_TYPEID.ZERG_DRONE.value)
        #all_worker_tags = collect_tags(all_workers)
        if len(all_extractors) > 0:
            a = 3
            b = 4
        self.ew_mgr.update(all_extractors, all_workers)

        for w in all_workers:
            if w.tag not in self.tmp:
                self.tmp.add(w.tag)

        print('len workers = ', len(all_workers))
        print('len tmp = ', len(self.tmp))

        actions = []
        actions += self._update_harvest_gas(all_extractors, all_workers)
        actions += self._update_harvest_mineral()

        am.push_actions(actions)
        self.step += 1

    def _update_harvest_gas(self, cur_all_extractors, cur_all_workers):
        actions = []

        for e_tag, num_workers in self.ew_mgr.extractor_tag_to_workers_num.items():
            e = find_by_tag(cur_all_extractors, e_tag)
            if not e:  # not a valid extractor tag due to unknown reason...
                continue
            if e.float_attr.build_progress < 1.0:  # extractor not yet built
                continue
            # if len(cur_all_workers) < 16:
            #     continue

            n_remain = ExtractorWorkerTagMgr.MAX_WORKERS_PER_EXTRACTOR - num_workers
            if n_remain <= 0:  # full on this extractor
                continue

            for w in cur_all_workers:
                target_tag = get_target_tag(w)
                if target_tag not in self.ew_mgr.extractor_tag_to_workers_num:  # this worker is not harvesting gas
                    actions += self.ew_mgr.act_worker_harvests_on_extractor(e.tag, w.tag)
                    break  # send only ONE worker to harvest the gas on this step

        return actions

    def _update_harvest_mineral(self):
        return []
