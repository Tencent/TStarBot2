from tstarbot.scout.tasks.scout_task import ScoutTask, ScoutAttackEscape
import tstarbot.scout.tasks.scout_task as st
from tstarbot.data.pool import macro_def as md


class ScoutExploreTask(ScoutTask):
  def __init__(self, scout, target, home, version):
    super(ScoutExploreTask, self).__init__(scout, home)
    self._target = target
    self._status = md.ScoutTaskStatus.DOING
    self._version = version
    self._monitor_pos = self._get_monitor_pos(self._version)
    self._base_arrived = False
    self._monitor_arrived = False
    self._attack_escape = None

  def type(self):
    return md.ScoutTaskType.EXPORE

  def target(self):
    return self._target

  def post_process(self):
    self._target.has_scout = False
    self._scout.is_doing_task = False
    if self._status == md.ScoutTaskStatus.SCOUT_DESTROY:
      if self._check_in_base_range() and not self._judge_task_done():
        self._target.has_enemy_base = True
        self._target.has_army = True
      else:
        self._target.has_scout = False
      #print('SCOUT explore_task post destory; target=', str(self._target))
    else:
      #print('SCOUT task post_process, status=', self._status, ';target=', str(self._target))
      pass

  def _do_task_inner(self, view_enemys, dc):
    if self._check_scout_lost():
      #print('SCOUT scout is lost, no action, tag=', self._scout.unit().tag)
      self._status = md.ScoutTaskStatus.SCOUT_DESTROY
      return None

    if self._status == md.ScoutTaskStatus.UNDER_ATTACK or self._check_attack():
      return self._exec_under_attack(view_enemys)

    if self._detect_enemy_by_ver(view_enemys, dc, self._version):
      self._status = md.ScoutTaskStatus.DONE
      return self._move_to_home()

    if not self._base_arrived and self._check_in_base_range():
      self._base_arrived = True

    if (self._base_arrived and not self._monitor_arrived and
        self._check_in_monitor_range()):
      self._monitor_arrived = True

    return self._exec_by_status()

  def _exec_explore(self):
    if self._version == st.EXPLORE_V1:
      if not self._base_arrived:
        return self._move_to_target(self._target.pos)
      elif self._judge_task_done():
        self._status = md.ScoutTaskStatus.DONE
        return self._move_to_home()
      else:
        return self._noop()
    elif self._version == st.EXPLORE_V2:
      if not self._base_arrived:
        return self._move_to_target(self._target.pos)
      elif not self._monitor_arrived and self._judge_task_done():
        return self._move_to_target(self._monitor_pos)
      else:
        return self._noop()
    else:
      if not self._base_arrived:
        #print("Scout V3 explore, base target, base={},monitor={}".format(
        #      self._base_arrived, self._monitor_arrived))
        return self._move_to_target(self._target.pos)
      elif not self._monitor_arrived and self._judge_task_done():
        #print("Scout V3 explore, monitor target,", self._monitor_pos)
        return self._move_to_target(self._monitor_pos)
      else:
        #print("Scout V3 explore, noop, base={},monitor={}".format(
        #      self._base_arrived, self._monitor_arrived))
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

    if not self._judge_task_done():
      self._target.has_army = True
    return act

  def _exec_by_status(self):
    if self._status == md.ScoutTaskStatus.DOING:
      return self._exec_explore()
    elif self._status == md.ScoutTaskStatus.DONE:
      return self._move_to_home()
    else:
      #print('SCOUT explore exec noop, scout status=', self._status)
      return self._noop()

  def _detect_enemy_by_ver(self, view_enemys, dc, ver):
    find_base, air_force = self._detect_enemy(view_enemys, dc)
    if ver >= st.EXPLORE_V3:
      return air_force
    else:
      return find_base

  def _detect_enemy(self, view_enemys, dc):
    bases = []
    queues = []
    airs = []
    armys = []
    main_base_buildings = []
    for enemy in view_enemys:
      if enemy.unit_type in md.BASE_UNITS:
        bases.append(enemy)
      elif enemy.unit_type == md.UNIT_TYPEID.ZERG_QUEEN.value:
        queues.append(enemy)
      elif enemy.unit_type in md.COMBAT_UNITS:
        armys.append(enemy)
      elif enemy.unit_type in md.COMBAT_AIR_UNITS:
        airs.append(enemy)
      elif enemy.unit_type in md.MAIN_BASE_BUILDS:
        main_base_buildings.append(enemy)
      else:
        continue

    find_base = False
    air_force = False
    for base in bases:
      dist = md.calculate_distance(self._target.pos[0],
                                   self._target.pos[1],
                                   base.float_attr.pos_x,
                                   base.float_attr.pos_y)
      #print('SCOUT base distance={}, base_range={}'.format(dist, SCOUT_BASE_RANGE))
      if dist < st.SCOUT_BASE_RANGE:
        self._target.has_enemy_base = True
        self._target.enemy_unit = base
        if len(armys) > 0:
          self._target.has_army = True
          #print('Scout find base, is_main_base:', dc.dd.scout_pool.has_enemy_main_base())
        if not dc.dd.scout_pool.has_enemy_main_base():
          #print('SCOUT find base, set main base')
          self._target.is_main = True
          if not find_base:
            find_base = True
            #print('SCOUT find enemy base, job finish, target=', str(self._target))

    for build in main_base_buildings:
      dist = md.calculate_distance(self._target.pos[0],
                                   self._target.pos[1],
                                   build.float_attr.pos_x,
                                   build.float_attr.pos_y)
      if dist < st.SCOUT_BASE_RANGE:
        #print('SCOUT find main_building in main base')
        self._target.has_enemy_base= True
        self._target.is_main = True
        if len(armys) > 0:
          self._target.has_army = True
        if not find_base:
          find_base = True

    for queue in queues:
      dist = md.calculate_distance(self._target.pos[0],
                                   self._target.pos[1],
                                   queue.float_attr.pos_x,
                                   queue.float_attr.pos_y)
      if dist < st.SCOUT_BASE_RANGE:
        self._target.has_enemy_base = True
        self._target.has_army = True
        if not dc.dd.scout_pool.has_enemy_main_base():
          #print('SCOUT find queue, set main base')
          self._target.is_main = True
          #print('SCOUT find enemy queue, job finish, target=', str(self._target))
        if not find_base:
          find_base = True
        if not air_force:
          air_force = True

    for unit in airs:
      dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                   self._scout.unit().float_attr.pos_y,
                                   unit.float_attr.pos_x,
                                   unit.float_attr.pos_y)
      if dist < st.SCOUT_SAFE_RANGE:
        #print('SCOUT deteck air unit around me, run')
        if not air_force:
          air_force = True
        break

    view_armys = []
    for enemy in armys:
      dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                   self._scout.unit().float_attr.pos_y,
                                   enemy.float_attr.pos_x,
                                   enemy.float_attr.pos_y)
      if dist < st.SCOUT_VIEW_RANGE:
        view_armys.append(enemy)
    if len(view_armys) > 0:
      self._scout.snapshot_armys = view_armys
    else:
      self._scout.snapshot_armys = None

    return find_base, air_force

  def _check_attack(self):
    attack = self._detect_attack()
    if attack:
      if self._status == md.ScoutTaskStatus.DOING:
        #print('SCOUT task turn DOING to UNDER_ATTACK, target=', str(self._target))
        self._status = md.ScoutTaskStatus.UNDER_ATTACK

    return attack

  def _check_in_base_range(self):
    dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                 self._scout.unit().float_attr.pos_y,
                                 self._target.pos[0],
                                 self._target.pos[1])
    if dist < st.SCOUT_CRUISE_ARRIVAED_RANGE:
      return True
    else:
      return False

  def _check_in_monitor_range(self):
    dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                 self._scout.unit().float_attr.pos_y,
                                 self._monitor_pos[0],
                                 self._monitor_pos[1])
    if dist < st.SCOUT_CRUISE_ARRIVAED_RANGE:
      return True
    else:
      return False

  def _judge_task_done(self):
    if self._target.has_enemy_base:
      return True
    elif self._target.has_army:
      return True
    else:
      return False

  def _get_monitor_pos(self, ver):
    if ver == st.EXPLORE_V3:
      diff_x = self._home[0] - self._target.pos[0]
      diff_y = self._home[1] - self._target.pos[1]
      r = (diff_x ** 2 + diff_y ** 2) ** 0.5
      monitor_pos = (self._target.pos[0] + 8 * diff_x / r, self._target.pos[1] + 8 * diff_y / r)
    else:
      avg_pos = self._target.area.calculate_avg()
      diff_x = avg_pos[0] - self._target.pos[0]
      diff_y = avg_pos[1] - self._target.pos[1]
      monitor_pos = (avg_pos[0] + 2.5 * diff_x, avg_pos[1] + 2.5 * diff_y)
      #print('task avg_pos={}, base_pos={} safe_pos={}'.format(
      #      avg_pos, self._target.pos, safe_pos))
    return monitor_pos
