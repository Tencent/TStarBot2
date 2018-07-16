import pysc2.lib.typeenums as tp
from enum import Enum
import numpy as np

from tstarbot.scout.tasks.scout_task import ScoutTask
import tstarbot.scout.tasks.scout_task as st
from tstarbot.data.pool import macro_def as md

class ForcedScoutStep(Enum):
  STEP_INIT = 0
  STEP_MOVE_TO_BASE = 1
  STEP_CIRCLE_MINERAL = 2
  STEP_RETREAT = 3


class ScoutForcedTask(ScoutTask):
  def __init__(self, scout, target, home):
    super(ScoutForcedTask, self).__init__(scout, home)
    self._target = target
    self._circle_path = []
    self._cur_circle_target = 0  # index of _circle_path
    self._cur_step = ForcedScoutStep.STEP_INIT

  def type(self):
    return md.ScoutTaskType.FORCED

  def post_process(self):
    self._target.has_scout = False
    self._scout.is_doing_task = False

    if self._status == md.ScoutTaskStatus.SCOUT_DESTROY:
      self._target.has_enemy_base = True
      self._target.has_army = True

  def _do_task_inner(self, view_enemys, dc):
    if self._check_scout_lost():
      self._status = md.ScoutTaskStatus.SCOUT_DESTROY
      return None

    if self._detect_enemy(view_enemys, dc):
      self._status = md.ScoutTaskStatus.DONE
      self._cur_step = ForcedScoutStep.STEP_RETREAT
      return self._move_to_home()

    if self._cur_step == ForcedScoutStep.STEP_INIT:
      # step one, move to target base
      action = self._move_to_target(self._target.pos)
      self._cur_step = ForcedScoutStep.STEP_MOVE_TO_BASE
      return action
    elif self._cur_step == ForcedScoutStep.STEP_MOVE_TO_BASE:
      # step two, circle target base
      if self._arrive_xy(self.scout().unit(),
                         self._target.pos[0], self._target.pos[1], 10):
        #self._generate_circle_path(self._target.area.m_pos)
        self._generate_base_around_path()
        self._cur_step = ForcedScoutStep.STEP_CIRCLE_MINERAL
        return self._move_to_target(self._circle_path[0])
      else:
        return None
    elif self._cur_step == ForcedScoutStep.STEP_CIRCLE_MINERAL:
      cur_target = self._circle_path[self._cur_circle_target]
      if self._arrive_xy(self.scout().unit(),
                         cur_target[0], cur_target[1], 1):
        self._cur_circle_target += 1
        if self._cur_circle_target < len(self._circle_path):
          return self._move_to_target(self._circle_path[self._cur_circle_target])
        else:
          self._cur_circle_target = 0
          return self._move_to_target(self._circle_path[self._cur_circle_target])
                #self._cur_step = ForcedScoutStep.STEP_RETREAT
                #return self._move_to_home()
      else:
        return None
    elif self._cur_step == ForcedScoutStep.STEP_RETREAT:
      # step three, retreat
      if self._arrive_xy(self.scout().unit(),
                         self._home[0], self._home[1], 10):
        self._status = md.ScoutTaskStatus.DONE

      return None

  def _generate_circle_path(self, m_pos):
    m_dim = len(m_pos)
    dis_mat = np.zeros((m_dim, m_dim))

    for i in range(m_dim):
      for j in range(m_dim):
        dis_mat[i][j] = self.distance(m_pos[i], m_pos[j])

    max_i = 0
    max_dist = 0

    for i in range(m_dim):
      for j in range(m_dim):
        if dis_mat[i][j] > max_dist:
          max_dist = dis_mat[i][j]
          max_i = i

    dist_list = []
    for i in range(m_dim):
      d = {'idx': i, 'distance': dis_mat[max_i][i]}
      dist_list.append(d)

    dist_list.sort(key=lambda x: x['distance'])

    for i in range(m_dim):
      self._circle_path.append(m_pos[dist_list[i]['idx']])

  def _generate_base_around_path(self):
    pos_arr_1 = []
    pos_arr_2 = []
    unit_pos = self._sort_target_unit_by_pos()
    centor_pos = self._target.area.ideal_base_pos
    for pos in unit_pos:
      diff_x = centor_pos[0] - pos[0]
      diff_y = centor_pos[1] - pos[1]
      pos_arr_1.append((centor_pos[0] + 1.2 * diff_x,
                        centor_pos[1] + 1.2 * diff_y))
      pos_arr_2.append((centor_pos[0] - 1.4 * diff_x,
                        centor_pos[1] - 1.4 * diff_y))

    pos_arr_2_first_half = pos_arr_2[:len(pos_arr_2)]
    pos_arr_2_sec_half = pos_arr_2[len(pos_arr_2):]

    for pos_0 in reversed(pos_arr_2_first_half):
      self._circle_path.append(pos_0)

    for pos_1 in pos_arr_1:
      self._circle_path.append(pos_1)

    for pos_2 in reversed(pos_arr_2_sec_half):
      self._circle_path.append(pos_2)

    #print("Scout path:", self._circle_path)

  def _sort_target_unit_by_pos(self):
    total = self._target.area.m_pos + self._target.area.g_pos
    #print('SCOUT before sort:', total)
    m_x = [item[0] for item in self._target.area.m_pos]
    m_y = [item[1] for item in self._target.area.m_pos]
    x_diff = abs(max(m_x) - min(m_x))
    y_diff = abs(max(m_y) - min(m_y))
    if x_diff > y_diff:
      '''sort by x axis'''
      #print('SCOUT sort by x axis')
      count = len(total)
      for i in range(1, count):
        item = total[i]
        j = i - 1
        while j >= 0:
          tmp = total[j]
          if tmp[0] > item[0]:
            total[j + 1] = total[j]
            total[j] = item
          j -= 1
    else:
      #print('SCOUT sort by y axis')
      '''sort by y axis '''
      count = len(total)
      for i in range(1, count):
        item = total[i]
        j = i - 1
        while j >= 0:
          tmp = total[j]
          if tmp[1] > item[1]:
            total[j + 1] = total[j]
            total[j] = item
          j -= 1
    #print('SCOUT after sort:', total)
    return total


  def _arrive_xy(self, u, target_x, target_y, error):
    x = u.float_attr.pos_x - target_x
    y = u.float_attr.pos_y - target_y
    distance = (x * x + y * y) ** 0.5

    return distance < error

  def distance(self, pos1, pos2):
    x = pos1[0] - pos2[0]
    y = pos1[1] - pos2[1]

    return (x * x + y * y) ** 0.5

  def _detect_enemy(self, view_enemys, dc):
    spool = dc.dd.scout_pool
    armys = []
    eggs = []
    spawning_on = False
    for enemy in view_enemys:
      if enemy.unit_type in md.COMBAT_UNITS:
        armys.append(enemy)
      elif enemy.unit_type == tp.UNIT_TYPEID.ZERG_EGG.value:
        eggs.append(enemy)
      elif enemy.unit_type == tp.UNIT_TYPEID.ZERG_SPAWNINGPOOL.value:
        if enemy.float_attr.build_progress >= st.BUILD_PROGRESS_FINISH:
          spawning_on = True
      else:
        pass

    me = (self._scout.unit().float_attr.pos_x,
          self._scout.unit().float_attr.pos_y)

    scout_armys = []
    for unit in armys:
      dist = md.calculate_distance(me[0], me[1],
                                   unit.float_attr.pos_x,
                                   unit.float_attr.pos_y)
      if dist < st.SCOUT_CRUISE_RANGE:
        scout_armys.append(unit)
    if len(eggs) > 0 and spawning_on:
      #print("SCOUT escape, may be zergling is building")
      return True

    return len(scout_armys) > 0
