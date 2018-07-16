from tstarbot.scout.tasks.scout_task import ScoutTask, ScoutAttackEscape
import tstarbot.scout.tasks.scout_task as st
from tstarbot.data.pool import macro_def as md
from tstarbot.data.pool import scout_pool as sp


class ScoutCruiseTask(ScoutTask):
  def __init__(self, scout, home, target):
    super(ScoutCruiseTask, self).__init__(scout, home)
    self._target = target
    self._paths = []
    self._curr_pos = 0
    self._generate_path()
    self._status = md.ScoutTaskStatus.DOING
    self._attack_escape = None

  def type(self):
    return md.ScoutTaskType.CRUISE

  def _do_task_inner(self, view_enemys, dc):
    if self._check_scout_lost():
      self._status = md.ScoutTaskStatus.SCOUT_DESTROY
      return None

    if self._status == md.ScoutTaskStatus.UNDER_ATTACK or self._check_attack():
      return self._exec_under_attack(view_enemys)

    self._detect_enemy(view_enemys, dc)
    return self._exec_by_status()

  def post_process(self):
    self._target.has_cruise = False
    self._scout.is_doing_task = False

  def _exec_by_status(self):
    if self._status == md.ScoutTaskStatus.DOING:
      return self._exec_cruise()
    elif self._status == md.ScoutTaskStatus.DONE:
      return self._move_to_home()
    else:
      #print('SCOUT cruise exec noop, scout status=', self._status)
      return self._noop()

  def _exec_under_attack(self, view_enemys):
    me = self._scout.unit()
    if self._attack_escape is None:
      self._attack_escape = ScoutAttackEscape()
      self._attack_escape.generate_path(view_enemys, me, self._home)

    me_pos = (me.float_attr.pos_x, me.float_attr.pos_y)
    if not self._attack_escape.curr_arrived(me_pos):
      #print('Scout exec_under_attack move to curr=',
      #      self._attack_escape.curr_pos())
      act = self._move_to_target(self._attack_escape.curr_pos())
    else:
      act = self._move_to_target(self._attack_escape.next_pos())
      #print('Scout exec_under_attack move to next=',
      #      self._attack_escape.curr_pos())

    if self._attack_escape.is_last_pos():
      self._status = md.ScoutTaskStatus.DONE

    return act

  def _exec_cruise(self):
    if self._curr_pos < 0 or self._curr_pos >= len(self._paths):
      self._curr_pos = 0
    pos = self._paths[self._curr_pos]
    if self._check_arrived_pos(pos):
      self._curr_pos += 1
    return self._move_to_target(pos)

  def _check_arrived_pos(self, pos):
    dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                 self._scout.unit().float_attr.pos_y,
                                 pos[0], pos[1])
    if dist < st.SCOUT_CRUISE_ARRIVAED_RANGE:
      return True
    else:
      return False

  def _generate_path(self):
    home_x = self._home[0]
    home_y = self._home[1]
    target_x = self._target.pos[0]
    target_y = self._target.pos[1]

    pos1 = ((home_x * 2) / 3 + target_x / 3, (home_y * 2)/3 + target_y / 3)
    pos2 = ((home_x + target_x)/2, (home_y + target_y)/2)
    pos3 = (pos2[0] - st.SCOUT_CRUISE_RANGE, pos2[1])
    pos4 = (home_x /3 + (target_x * 2) / 3, home_y / 3 + (target_y * 2) / 3)
    pos5 = (pos2[0] + st.SCOUT_CRUISE_RANGE, pos2[1])

    self._paths.append(pos1)
    self._paths.append(pos3)
    self._paths.append(pos2)
    self._paths.append(pos4)
    self._paths.append(pos5)

  def _check_attack(self):
    attack = self._detect_attack()
    if attack:
      #print('SCOUT task turn DOING to UNDER_ATTACK, target=', str(self._target))
      self._status = md.ScoutTaskStatus.UNDER_ATTACK
      return True
    else:
      return False

  def _detect_enemy(self, view_enemys, dc):
    spool = dc.dd.scout_pool
    armys = []
    for enemy in view_enemys:
      if enemy.unit_type in md.COMBAT_UNITS:
        armys.append(enemy)

    me = (self._scout.unit().float_attr.pos_x,
          self._scout.unit().float_attr.pos_y)

    scout_armys = []
    for unit in armys:
      dist = md.calculate_distance(me[0], me[1],
                                   unit.float_attr.pos_x,
                                   unit.float_attr.pos_y)
      if dist < st.SCOUT_CRUISE_RANGE:
        scout_armys.append(unit)
        break
    if len(scout_armys) > 0:
      alarm = sp.ScoutAlarm()
      alarm.enmey_armys = scout_armys
      if not spool.alarms.full():
        spool.alarms.put(alarm)
