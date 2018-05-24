"""Resource Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import random
from copy import deepcopy
import numpy as np

from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, RACE

from tstarbot.production.build_cmd import BuildCmdHarvest
from tstarbot.data.pool.macro_def import AllianceType


def dist(unit1, unit2):
    """ return Euclidean distance ||unit1 - unit2|| """
    return ((unit1.float_attr.pos_x - unit2.float_attr.pos_x)**2 +
            (unit1.float_attr.pos_y - unit2.float_attr.pos_y)**2)**0.5


def collect_units(units, unit_type, alliance=1):
    return [u for u in units
            if u.unit_type == unit_type and u.int_attr.alliance == alliance]


def collect_units_by_tags(units, tags):
    uu = []
    for tag in tags:
        u = find_by_tag(units, tag)
        if u:
            uu.append(u)
    return uu


def find_by_tag(units, tag):
    for u in units:
        if u.tag == tag:
            return u
    return None


def find_first_if(units, f=lambda x: True):
    for u in units:
        if f(u):
            return u
    return None


def find_n_if(units, n, f=lambda x: True):
    ru = []
    for u in units:
        if len(ru) >= n:
            break
        if f(u):
            ru.append(u)
    return ru


def sort_units_by_distance(units, unit):
    def my_dist(x_u):
        return dist(x_u, unit)
    return sorted(units, key=my_dist)


def get_target_tag(unit, idx=0):
    if unit.orders:
        return unit.orders[idx].target_tag
    return None


def is_harvesting(unit):
    if unit.orders:
        ab_id = unit.orders[0].ability_id
        return (ab_id == ABILITY_ID.HARVEST_GATHER.value or
                ab_id == ABILITY_ID.HARVEST_GATHER_DRONE.value)
    return False


def get_unfilled_workers(unit):
    return unit.int_attr.ideal_harvesters - unit.int_attr.assigned_harvesters


def has_order(unit):
    return len(unit.orders) > 0


def func_is_harvesting_local_vb(base_instance):
    def f_impl(w_unit):
        target_tag = get_target_tag(w_unit)
        return target_tag in base_instance.vb_set
    return f_impl


def func_is_harvesting_vb(extractor):
    def f_impl(w_unit):
        target_tag = get_target_tag(w_unit)
        return target_tag == extractor.tag
    return f_impl


def func_is_harvesting_local_mineral(base_instance):
    def f_impl(w_unit):
        target_tag = get_target_tag(w_unit)
        return target_tag in base_instance.mineral_set
    return f_impl


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


def act_rally_worker(target_tag, base_tag):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
        ABILITY_ID.RALLY_HATCHERY_WORKERS.value
    action.action_raw.unit_command.target_unit_tag = target_tag
    action.action_raw.unit_command.unit_tags.append(base_tag)
    return action


def act_stop(unit_tag):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ABILITY_ID.STOP.value
    action.action_raw.unit_command.unit_tags.append(unit_tag)
    return action


def append_valid_action(actions, action):
    if action:
        actions.append(action)
        return True
    return False


class BaseResourceMgr(object):
    def __init__(self, dc):
        pass

    def update(self, obs_mgr, act_mgr):
        pass

    def reset(self):
        pass


class ZergResourceMgr(BaseResourceMgr):
    def __init__(self, dc):
        super(ZergResourceMgr, self).__init__(dc)
        self.all_bases = None
        self.all_extractors = None
        self.all_workers = None
        self.all_minerals = None
        self.is_gas_first = False
        self.verbose = 0
        self.step = 0
        self._rebalance_last_tried_gameloop = -1
        self._init_config(dc)

    def reset(self):
        super(ZergResourceMgr, self).reset()

        self.all_bases = None
        self.all_extractors = None
        self.all_workers = None
        self.all_minerals = None
        self.is_gas_first = False
        self.step = 0
        self._rebalance_last_tried_gameloop = -1

    def update(self, dc, am):
        super(ZergResourceMgr, self).update(dc, am)

        self._update_data(dc)

        # parse commands
        accepted_cmds = [BuildCmdHarvest]
        for _ in range(dc.dd.build_command_queue.size()):
            cmd = dc.dd.build_command_queue.get()
            if type(cmd) not in accepted_cmds:
                # put back unknown command
                dc.dd.build_command_queue.put(cmd)
                if self.verbose >= 4:
                    print("Warning: ZergResourceMgr: unknown command {}".format(
                        cmd))
                continue
            if type(cmd) == BuildCmdHarvest:
                self.is_gas_first = cmd.gas_first
                if self.verbose >= 2:
                    print(
                        "ZergResourceMgr: step={}, receive command gas_first"
                        "= {}".format(self.step, self.is_gas_first)
                    )

        # perform actions
        actions = []
        actions += self._update_base_instance()
        actions += self._update_idle_workers()
        actions += self._rebalance_workers()
        am.push_actions(actions)
        self.step += 1

    def _init_config(self, dc):
        if hasattr(dc, 'config'):
            if hasattr(dc.config, 'resource_verbose'):
                self.verbose = dc.config.resource_verbose

    def _update_data(self, dc):
        self.dc = dc

        units = dc.sd.obs['units']
        self.all_bases = collect_units(units, UNIT_TYPEID.ZERG_HATCHERY.value) \
            + collect_units(units, UNIT_TYPEID.ZERG_LAIR.value)
        self.all_extractors = collect_units(units,
                                            UNIT_TYPEID.ZERG_EXTRACTOR.value)
        self.all_workers = collect_units(units, UNIT_TYPEID.ZERG_DRONE.value)
        self.all_minerals = collect_units(
            units, UNIT_TYPEID.NEUTRAL_MINERALFIELD.value,
            alliance=AllianceType.NEUTRAL.value)

        if self.verbose >= 4:
            print('ZergResourceMgr: step {}'.format(self.step))
            print_harvester(self.all_bases, name='all_basese')
            print_harvester(self.all_extractors, name='all_extractors')
            print('len workers = ', len(self.all_workers))

    def _update_base_instance(self):
        actions = []
        for base_instance in self.dc.dd.base_pool.bases.values():
            act = self._update_local_base(base_instance)
            append_valid_action(actions, act)
            act = self._update_local_extractors(base_instance)
            append_valid_action(actions, act)
        return actions

    def _update_local_base(self, base_instance):
        base = base_instance.unit  # it must have only ONE base
        n_unfilled = get_unfilled_workers(base)
        if n_unfilled == 0:  # do nothing when balanced
            return None

        local_workers = collect_units_by_tags(self.all_workers,
                                              base_instance.worker_set)

        # only add a worker when mineral-first is True
        if not self.is_gas_first:
            if n_unfilled > 0:
                # under-filled: grab a worker harvesting gas,
                # and have the worker harvest mineral
                worker = find_first_if(
                    units=local_workers,
                    f=func_is_harvesting_local_vb(base_instance)
                )
                if worker:
                    return self._harvest_on_base(worker, base)

        if n_unfilled < 0:
            # over-filled: stop a worker harvesting on mineral
            worker = find_first_if(
                units=local_workers,
                f=func_is_harvesting_local_mineral(base_instance)
            )
            if worker:
                return act_stop(worker.tag)

        return None

    def _update_local_extractors(self, base_instance):
        local_workers = []
        local_extractors = collect_units_by_tags(self.all_extractors,
                                                 base_instance.vb_set)
        for e in local_extractors:
            n_unfilled = get_unfilled_workers(e)
            if n_unfilled == 0:  # do nothing when balanced
                continue

            if not local_workers:
                local_workers = collect_units_by_tags(
                    self.all_workers, base_instance.worker_set)

            # only add a worker when gas-first is True
            if self.is_gas_first:
                if n_unfilled > 0:
                    # under-filled: grab a worker harvesting  and have it work
                    worker = find_first_if(
                        units=local_workers,
                        f=func_is_harvesting_local_mineral(base_instance)
                    )
                    if worker:
                        return self._harvest_on_extractor(worker, e)

            if n_unfilled < 0:
                # over-filled: stop a worker
                worker = find_first_if(
                    units=local_workers,
                    f=func_is_harvesting_vb(e)
                )
                if worker:
                    return act_stop(worker.tag)

    def _rebalance_workers(self):
        actions = []
        b_from, b_to = self._can_rebalance_workers()
        if not b_from or not b_to:
            return actions

        local_workers = collect_units_by_tags(self.all_workers,
                                              b_from.worker_set)
        workers_migrate = find_n_if(units=local_workers, n=3,
                                    f=func_is_harvesting_local_mineral(b_from))
        for w in workers_migrate:
            base = b_to.unit
            act = self._harvest_on_base(w, base)
            append_valid_action(actions, act)
        self._rebalance_last_tried_gameloop = self.dc.sd.obs['game_loop']
        return actions

    def _can_rebalance_workers(self):
        # always do it for the first time no matter the game_loop;
        # or don't do it too frequent
        if self._rebalance_last_tried_gameloop is not -1:
            game_loop = self.dc.sd.obs['game_loop']
            if game_loop - self._rebalance_last_tried_gameloop < 24*15:
                return None, None

        base_instances = list(self.dc.dd.base_pool.bases.values())
        if len(base_instances) != 2:
            return None, None  # currently only rebalance for 2 bases

        bb = sorted(base_instances,
                    key=lambda b: b.unit.int_attr.assigned_harvesters)

        b_to, b_from = bb[0], bb[1]

        # base_to must be almost built
        if b_to.unit.float_attr.build_progress < 0.98:
            return None, None

        # base_to must have empty harvesters
        n_from = b_from.unit.int_attr.assigned_harvesters
        n_to = b_to.unit.int_attr.assigned_harvesters
        if n_to > 0:
            return None, None
        return b_from, b_to

    def _update_idle_workers(self):
        actions = []
        idle_workers = [w for w in self.all_workers if not has_order(w)]
        for w in idle_workers:
            bases_sorted = sort_units_by_distance(self.all_bases, w)
            extractors_sorted = sort_units_by_distance(self.all_extractors, w)
            if not self.is_gas_first:  # mineral first
                act = self._harvest_on_first_unfilled_base(w, bases_sorted)
                if append_valid_action(actions, act):
                    continue
                act = self._harvest_on_first_unfilled_extractor(
                    w, extractors_sorted)
                if append_valid_action(actions, act):
                    continue
            else:  # gas first
                act = self._harvest_on_first_unfilled_extractor(
                    w, extractors_sorted)
                if append_valid_action(actions, act):
                    continue
                act = self._harvest_on_first_unfilled_base(w, bases_sorted)
                if append_valid_action(actions, act):
                    continue
        return actions

    def _harvest_on_first_unfilled_base(self, worker, bases):
        for b in bases:
            if get_unfilled_workers(b) > 0:
                action = self._harvest_on_base(worker, b)
                if action:
                    return action
        return None

    def _harvest_on_first_unfilled_extractor(self, worker, extractors):
        for e in extractors:
            if get_unfilled_workers(e) > 0:
                action = self._harvest_on_extractor(worker, e)
                if action:
                    return action
        return None

    def _harvest_on_base(self, worker, base):
        # for the local minerals in base's neighborhood,
        # find the one with largest remaining content
        base_instance = self.dc.dd.base_pool.bases[base.tag]
        local_minerals = collect_units_by_tags(self.all_minerals,
                                               base_instance.mineral_set)
        if local_minerals:
            mineral = max(local_minerals,
                          key=lambda u: u.int_attr.mineral_contents)
            return act_worker_harvests_on_target(mineral.tag, worker.tag)
        return None

    def _harvest_on_extractor(self, worker, extractor):
        if worker and extractor:
            return act_worker_harvests_on_target(extractor.tag, worker.tag)
        return None
