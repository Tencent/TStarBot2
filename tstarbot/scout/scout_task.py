from tstarbot.data.pool import macro_def as md
from tstarbot.data.pool import scout_pool as sp
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp
from collections import deque

MAX_SCOUT_HISTORY = 10
SCOUT_BASE_RANGE = 13
class ScoutTask(object):
    def __init__(self, scout, home):
        self._scout = scout
        self._home = home
        self._status = md.ScoutTaskStatus.INIT
        self._scout_history = deque(maxlen=MAX_SCOUT_HISTORY)

    def scout(self):
        return self._scout

    def type(self):
        raise NotImplementedError

    def status(self):
        return self._status

    def do_task(self, view_enemys):
        return self._do_task_inner(view_enemys)

    def post_process(self):
        raise NotImplementedError

    def _do_task_inner(self, view_enemys):
        raise NotImplementedError

    def _detect_attack(self):
        return False

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

    def _update_history(self, scout_unit):
        if len(self._scout_history) == MAX_SCOUT_HISTORY:
            self._scout_history.pop()
        self._scout_history.appendleft(scout_unit)

class ScoutExploreTask(ScoutTask):
    def __init__(self, scout, target, home):
        super(ScoutExploreTask, self).__init__(scout, home)
        self._target = target

    def type(self):
        return md.ScoutTaskType.EXPORE

    def target(self):
        return self._target

    def post_process(self):
        if self._status == md.ScoutTaskStatus.SCOUT_DESTROY:
            if self._check_in_target_range() and not self._judge_task_done():
                self._target.has_enemy_base = True
                self._target.has_army = True
                self._target.has_scout = False
            print('SCOUT explore_task destory; target=', str(self._target))
            return None

    def _do_task_inner(self, view_enemys):
        if self._check_scout_lost():
            #print('SCOUT scout is lost, no action, tag=', self._scout.unit().tag)
            self._status = md.ScoutTaskStatus.SCOUT_DESTROY
            return None

        if self._detect_attack():
            self._status = md.ScoutTaskStatus.UNDER_ATTACK

        if self._detect_enemy(view_enemys):
            self._status = md.ScoutTaskStatus.DONE
            return self._move_to_home()

        if self._check_in_target_range():
           if self._judge_task_done():
               self._status = md.ScoutTaskStatus.DONE
        else:
           if self._status == md.ScoutTaskStatus.INIT:
               self._status = md.ScoutTaskStatus.DOING 

        return self._exec_by_status()

    def _exec_by_status(self):
        if self._status == md.ScoutTaskStatus.DOING:
            return self._move_to_target(self._target.pos)
        elif self._status == md.ScoutTaskStatus.DONE:
            return self._move_to_home()
        else:
            print('SCOUT exec noop, scout status=', self._status)
            return self._noop()

    def _detect_enemy(self, view_enemys):
        bases = []
        queues = []
        armys = []
        buildings = []
        for enemy in view_enemys:
            if enemy.unit_type in md.BASE_UNITS:
                bases.append(enemy)
            elif enemy.unit_type == md.UNIT_TYPEID.ZERG_QUEEN.value:
                queues.append(enemy)
            elif enemy.unit_type in md.COMBAT_UNITS:
                armys.append(enemy)
            elif enemy.unit_type in md.BUILDING_UNITS:
                buildings.append(enemy)
            else:
                continue

        done = False
        for base in bases:
            dist = md.calculate_distance(self._target.pos[0], 
                                         self._target.pos[1],
                                         base.float_attr.pos_x,
                                         base.float_attr.pos_y)
            if dist < SCOUT_BASE_RANGE:
                self._target.has_enemy_base = True
                self._target.enemy_unit = base
                if len(armys) > 0:
                    self._target.has_army = True
                if len(buildings) > 0:
                    self._target.is_main = True
                print('SCOUT find enemy base, job finish, target=', str(self._target))
                if not done:
                    done = True

        for queue in queues:
            dist = md.calculate_distance(self._target.pos[0], 
                                         self._target.pos[1],
                                         queue.float_attr.pos_x,
                                         queue.float_attr.pos_y)
            if dist < SCOUT_BASE_RANGE:
                self._target.has_enemy_base = True
                self._target.has_army = True
                if len(buildings) > 0:
                    self._target.is_main = True
                print('SCOUT find enemy queue, job finish, target=', str(self._target))
                return True

        return done

    def _check_scout_lost(self):
        return self._scout.is_lost()

    def _check_in_target_range(self):
        dist = md.calculate_distance(self._scout.unit().float_attr.pos_x, 
                                     self._scout.unit().float_attr.pos_y,
                                     self._target.pos[0],
                                     self._target.pos[1])
        if dist < SCOUT_BASE_RANGE:
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

