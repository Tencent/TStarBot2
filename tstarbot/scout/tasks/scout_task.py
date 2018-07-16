from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp
from tstarbot.data.pool import macro_def as md

SCOUT_BASE_RANGE = 10
SCOUT_SAFE_RANGE = 12
SCOUT_VIEW_RANGE = 10
SCOUT_CRUISE_RANGE = 5
SCOUT_CRUISE_ARRIVAED_RANGE = 1
BUILD_PROGRESS_FINISH = 1.0

EXPLORE_V1 = 0
EXPLORE_V2 = 1
EXPLORE_V3 = 2


class ScoutTask(object):
  def __init__(self, scout, home):
    self._scout = scout
    self._home = home
    self._status = md.ScoutTaskStatus.INIT
    self._last_health = None

  def scout(self):
    return self._scout

  def type(self):
    raise NotImplementedError

  def status(self):
    return self._status

  def do_task(self, view_enemys, dc):
    return self._do_task_inner(view_enemys, dc)

  def post_process(self):
    raise NotImplementedError

  def _do_task_inner(self, view_enemys, dc):
    raise NotImplementedError

  def _move_to_target(self, pos):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = tp.ABILITY_ID.SMART.value
    action.action_raw.unit_command.target_world_space_pos.x = pos[0]
    action.action_raw.unit_command.target_world_space_pos.y = pos[1]
    action.action_raw.unit_command.unit_tags.append(self._scout.unit().tag)
    return action

  def _move_to_home(self):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = tp.ABILITY_ID.SMART.value
    action.action_raw.unit_command.target_world_space_pos.x = self._home[0]
    action.action_raw.unit_command.target_world_space_pos.y = self._home[1]
    action.action_raw.unit_command.unit_tags.append(self._scout.unit().tag)
    return action

  def _noop(self):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = tp.ABILITY_ID.INVALID.value
    return action

  def _detect_attack(self):
    attack = False
    current_health = self._scout.unit().float_attr.health
    if self._last_health is None:
      self._last_health = current_health
      return attack

    if self._last_health > current_health:
      attack = True

    self._last_health = current_health
    return attack

  def _detect_recovery(self):
    curr_health = self._scout.unit().float_attr.health
    max_health = self._scout.unit().float_attr.health_max
    return curr_health == max_health

  def _check_scout_lost(self):
    return self._scout.is_lost()

  def check_end(self, view_enemys, dc):
    find_base = False
    find_queue = False
    for enemy in view_enemys:
      if enemy.unit_type == md.UNIT_TYPEID.ZERG_QUEEN.value:
        dist = md.calculate_distance(self._target.pos[0],
                                     self._target.pos[1],
                                     enemy.float_attr.pos_x,
                                     enemy.float_attr.pos_y)
        if dist < SCOUT_BASE_RANGE:
          find_queue = True
          break
      elif enemy.unit_type in md.BASE_UNITS:
        dist = md.calculate_distance(self._target.pos[0], self._target.pos[1],
                                     enemy.float_attr.pos_x, enemy.float_attr.pos_y)
        if dist < SCOUT_BASE_RANGE:
          find_base = True
          break
      else:
        continue

    return find_base or find_queue 


class ScoutAttackEscape(object):
  def __init__(self):
    self._paths = []
    self._curr = 0

  def curr_arrived(self, me_pos):
    curr_pos = self._paths[self._curr]
    dist = md.calculate_distance(curr_pos[0], curr_pos[1],
                                 me_pos[0], me_pos[1])
    if dist <= SCOUT_CRUISE_ARRIVAED_RANGE:
      return True
    else:
      return False

  def curr_pos(self):
    return self._paths[self._curr]

  def next_pos(self):
    self._curr += 1
    return self._paths[self._curr]

  def is_last_pos(self):
    last = len(self._paths) - 1
    return self._curr == last

  def generate_path(self, view_enemys, me, home_pos):
    airs = []
    for enemy in view_enemys:
      if enemy.unit_type in md.COMBAT_AIR_UNITS:
        dist = md.calculate_distance(me.float_attr.pos_x,
                                     me.float_attr.pos_y,
                                     enemy.float_attr.pos_x,
                                     enemy.float_attr.pos_y)
        if dist < SCOUT_SAFE_RANGE:
          airs.append(enemy)
      else:
        continue

    enemy_pos = None
    total_x = 0.0
    total_y = 0.0
    if len(airs) > 0:
      for unit in airs:
        total_x += unit.float_attr.pos_x
        total_y += unit.float_attr.pos_y
      enemy_pos = (total_x / len(airs), total_y / len(airs))
    else:
      total_x = me.float_attr.pos_x + 1
      total_y = me.float_attr.pos_y + 1
      enemy_pos = (total_x, total_y)
    self._generate_path(home_pos, (me.float_attr.pos_x, 
                        me.float_attr.pos_y), enemy_pos)
    #print("SCOUT escape attack, path=", self._paths)

  def _generate_path(self, home_pos, me_pos, enemy_pos):
    diff_x = me_pos[0] - enemy_pos[0]
    diff_y = me_pos[1] - enemy_pos[1]
    pos_1 = (me_pos[0] + diff_x, me_pos[1] + diff_y)
    pos_2 = (pos_1[0], home_pos[1])
    self._paths.append(pos_1)
    self._paths.append(pos_2)
    self._paths.append(home_pos)


