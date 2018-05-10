"""Scout Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp
import tstarbot.scout.scout_task as st
import tstarbot.data.pool.macro_def as md

from tstarbot.data.pool.worker_pool import EmployStatus
from tstarbot.data.pool.scout_pool import Scout

class BaseScoutMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass

    def reset(self):
        pass

DEF_EXPLORE_VER = 0

class ZergScoutMgr(BaseScoutMgr):
    def __init__(self, dc):
        super(ZergScoutMgr, self).__init__()
        self._tasks = []
        self._init_config(dc)
        self._forced_scout_count = 1

    def _init_config(self, dc):
        if not hasattr(dc, 'config'):
            self._explore_ver = DEF_EXPLORE_VER
            return

        if hasattr(dc.config, 'scout_explore_version'):
            self._explore_ver = dc.config.scout_explore_version
        else:
            self._explore_ver = DEF_EXPLORE_VER 
        # print('Scout explore version=', self._explore_ver)

        if hasattr(dc.config, 'max_forced_scout_count'):
            self._forced_scout_count = dc.config.max_forced_scout_count

    def reset(self):
        self._tasks = []

    def update(self, dc, am):
        super(ZergScoutMgr, self).update(dc, am)
        #print('SCOUT scout_mgr update, task_num=', len(self._tasks))
        self._dispatch_task(dc)
        self._check_task(dc)

        actions = []
        # observe the enemy
        units = dc.sd.obs['units']
        view_enemys = []
        for u in units:
            if u.int_attr.alliance == md.AllianceType.ENEMY.value:
                view_enemys.append(u)

        #print('SCOUT view enemy number:', len(view_enemys))
        for task in self._tasks:
            act = task.do_task(view_enemys, dc)
            if act is not None:
                actions.append(act)

        if len(actions) > 0:
            am.push_actions(actions)

    def _check_task(self, dc):
        keep_tasks = []
        done_tasks = []
        for task in self._tasks:
            if task.status() == md.ScoutTaskStatus.DONE:
                done_tasks.append(task)
            elif task.status() == md.ScoutTaskStatus.SCOUT_DESTROY:
                done_tasks.append(task)
            elif task.status() == md.ScoutTaskStatus.UNDER_ATTACK:
                done_tasks.append(task)
            else:
                keep_tasks.append(task)

        for task in done_tasks:
            task.post_process()

            if task.type() == md.ScoutTaskType.FORCED \
                and task.status() == md.ScoutTaskStatus.DONE:
                dc.dd.scout_pool.remove_scout(task.scout().unit().int_attr.tag)

        self._tasks = keep_tasks

    def _dispatch_task(self, dc):
        self._dispatch_cruise_task(dc)
        self._dispatch_explore_task(dc)

        if self._forced_scout_count > 0:
            ret = self._dispatch_forced_scout_task(dc)
            if ret:
                self._forced_scout_count -= 1

    def _dispatch_explore_task(self, dc):
        sp = dc.dd.scout_pool
        scout = sp.select_scout()
        target = sp.find_furthest_idle_target()
        if scout is None or target is None:
            # not need dispatch task
            return
        task = st.ScoutExploreTask(scout, target, sp.home_pos, self._explore_ver)
        scout.is_doing_task = True
        target.has_scout = True
        self._tasks.append(task)

    def _dispatch_cruise_task(self, dc):
        sp = dc.dd.scout_pool
        scout = sp.select_scout()
        target = sp.find_cruise_target()
        if scout is None or target is None:
            return

        task = st.ScoutCruiseTask(scout, sp.home_pos, target)
        scout.is_doing_task = True
        target.has_cruise = True
        self._tasks.append(task)

    def _dispatch_forced_scout_task(self, dc):
        sp = dc.dd.scout_pool

        target = sp.find_forced_scout_target()
        if target is None:
            return False

        scout = sp.select_drone_scout()
        if scout is None:
            return False

        task = st.ScoutForcedTask(scout, target, sp.home_pos)
        scout.is_doing_task = True
        target.has_scout = True
        self._tasks.append(task)

        return True
