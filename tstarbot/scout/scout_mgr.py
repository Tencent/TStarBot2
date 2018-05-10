"""Scout Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp
import tstarbot.scout.scout_task as st
import tstarbot.data.pool.macro_def as md


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
        self._scouts = {} # tagid -> unit
        self._tasks = []
        self._init_config(dc)

    def _init_config(self, dc):
        if not hasattr(dc, 'config'):
            self._explore_ver = DEF_EXPLORE_VER
            return

        if hasattr(dc.config, 'scout_explore_version'):
            self._explore_ver = dc.config.scout_explore_version
        else:
            self._explore_ver = DEF_EXPLORE_VER 
        print('Scout explore version=', self._explore_ver)

    def reset(self):
        self._scouts = {}
        self._tasks = []

    def update(self, dc, am):
        super(ZergScoutMgr, self).update(dc, am)
        #print('SCOUT scout_mgr update, task_num=', len(self._tasks))
        self._dispatch_task(dc)
        self._check_task()

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

        '''
        for (k,u) in self._scouts.items():
            action = self.goto_xy(u, 50, 40)
            actions.append(action)
        '''
        if len(actions) > 0:
            am.push_actions(actions)

    def goto_xy(self, u, target_x, target_y):
        action = sc_pb.Action()
        action.action_raw.unit_command.unit_tags.append(u.int_attr.tag)
        action.action_raw.unit_command.ability_id = tp.ABILITY_ID.SMART.value
        action.action_raw.unit_command.target_world_space_pos.x = target_x
        action.action_raw.unit_command.target_world_space_pos.y = target_y
        return action

    def arrive_xy(self, u, target_x, target_y):
        x = u.float_attr.pos_x - target_x
        y = u.float_attr.pos_y - target_y
        distance = (x*x + y*y) ** 0.5

        return distance < 0.1

    def _check_task(self):
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

        self._tasks = keep_tasks

    def _dispatch_task(self, dc):
        self._dispatch_cruise_task(dc)
        self._dispatch_explore_task(dc)

    def _dispatch_explore_task(self, dc):
        sp = dc.dd.scout_pool
        scout = sp.select_scout()
        target = sp.find_furthest_idle_target()
        if scout is None or target is None:
            '''not need dispatch task '''
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

