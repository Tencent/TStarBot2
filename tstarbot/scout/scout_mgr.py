"""Scout Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tstarbot.scout.tasks.scout_task as st
from tstarbot.scout.tasks.explor_task import ScoutExploreTask
from tstarbot.scout.tasks.cruise_task import ScoutCruiseTask
from tstarbot.scout.tasks.force_scout import ScoutForcedTask

import tstarbot.scout.oppo_monitor as om
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
    self._tasks = []
    self._oppo_monitor = om.OppoMonitor()
    self._explore_ver = DEF_EXPLORE_VER
    self._forced_scout_count = 0
    self._assigned_forced_scout_count = 0

    # explore task rl
    self._rl_support = False
    self._explore_task_model = None
    self._map_max_x = 0
    self._map_max_y = 0

    self._init_config(dc)

  def _init_config(self, dc):
    if not hasattr(dc, 'config'):
      return

    if hasattr(dc.config, 'scout_explore_version'):
      self._explore_ver = dc.config.scout_explore_version
    #print('Scout explore version=', self._explore_ver)

    if hasattr(dc.config, 'max_forced_scout_count'):
      self._forced_scout_count = dc.config.max_forced_scout_count

    if hasattr(dc.config, 'scout_explore_task_model'):
      self._explore_task_model = dc.config.scout_explore_task_model

    if hasattr(dc.config, 'scout_map_max_x'):
      self._map_max_x = dc.config.scout_map_max_x

    if hasattr(dc.config, 'scout_map_max_y'):
      self._map_max_y = dc.config.scout_map_max_y

    if hasattr(dc.config, 'explore_rl_support'):
      self._rl_support = dc.config.explore_rl_support

  def reset(self):
    self._tasks = []
    self._assigned_forced_scout_count = 0
    self._oppo_monitor = om.OppoMonitor()

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

    self._oppo_monitor.analysis(dc)
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
      else:
        keep_tasks.append(task)

    for task in done_tasks:
      task.post_process()

      if task.type() == md.ScoutTaskType.FORCED \
        and task.status() == md.ScoutTaskStatus.DONE:
        dc.dd.scout_pool.remove_scout(task.scout().unit().int_attr.tag)

    self._tasks = keep_tasks

  def _dispatch_task(self, dc):
    if self._forced_scout_count > self._assigned_forced_scout_count:
      ret = self._dispatch_forced_scout_task(dc)
      if ret:
        self._assigned_forced_scout_count += 1

    if self._explore_ver < st.EXPLORE_V3:
      self._dispatch_cruise_task(dc)

    self._dispatch_explore_task(dc)

  def _dispatch_explore_task(self, dc):
    sp = dc.dd.scout_pool
    scout = sp.select_scout()
    if self._explore_ver >= st.EXPLORE_V3:
      target = sp.find_enemy_subbase_target()
    else:
      target = sp.find_furthest_idle_target()
    if scout is None or target is None:
      # not need dispatch task
      return

    if self._rl_support:
      # rl-based explore task
      if self._explore_task_model is None:
        raise ValueError('no valid explore_task_model provided!')

      from tstarbot.scout.tasks.explor_task_rl import ScoutExploreTaskRL

      task = ScoutExploreTaskRL(scout, target, sp.home_pos,
                                self._explore_task_model,
                                self._map_max_x, self._map_max_y)
      self._rl_support = False  # currently only start one
    else:
      # rule base explore task
      task = ScoutExploreTask(scout, target, sp.home_pos, self._explore_ver)

    scout.is_doing_task = True
    target.has_scout = True
    self._tasks.append(task)

  def _dispatch_cruise_task(self, dc):
    sp = dc.dd.scout_pool
    scout = sp.select_scout()
    target = sp.find_cruise_target()
    if scout is None or target is None:
      return

    task = ScoutCruiseTask(scout, sp.home_pos, target)
    scout.is_doing_task = True
    target.has_cruise = True
    self._tasks.append(task)

  def _dispatch_forced_scout_task(self, dc):
    sp = dc.dd.scout_pool

    target = sp.find_forced_scout_target()
    #target = sp.find_furthest_idle_target()
    if target is None:
      return False

    scout = sp.select_drone_scout()
    if scout is None:
      return False

    task = ScoutForcedTask(scout, target, sp.home_pos)
    scout.is_doing_task = True
    target.has_scout = True
    self._tasks.append(task)

    return True

