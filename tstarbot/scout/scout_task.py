from tstarbot.data.pool import macro_def as md
from tstarbot.data.pool import scout_pool as sp
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp
from enum import Enum
import numpy as np

BUILD_PROGRESS_FINISH = 1.0
MAX_SCOUT_HISTORY = 10
SCOUT_BASE_RANGE = 10
SCOUT_SAFE_RANGE = 12
SCOUT_CRUISE_RANGE = 5
SCOUT_CRUISE_ARRIVAED_RANGE = 1
SCOUT_VIEW_RANGE = 10

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
            #print('scout is attack')
            attack = True

        self._last_health = current_health
        return attack

    def _detect_recovery(self):
        curr_health = self._scout.unit().float_attr.health
        max_health = self._scout.unit().float_attr.health_max
        return curr_health == max_health

    def _check_scout_lost(self):
        return self._scout.is_lost()

EXPLORE_V1 = 0
EXPLORE_V2 = 1
EXPLORE_V3 = 2

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
        if self._version == EXPLORE_V1:
            if not self._base_arrived:
                return self._move_to_target(self._target.pos)
            elif self._judge_task_done():
                self._status = md.ScoutTaskStatus.DONE
                return self._move_to_home()
            else:
                return self._noop()
        elif self._version == EXPLORE_V2:
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
        if ver >= EXPLORE_V3:
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
            if dist < SCOUT_BASE_RANGE:
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
            if dist < SCOUT_BASE_RANGE:
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
            if dist < SCOUT_BASE_RANGE:
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
             if dist < SCOUT_SAFE_RANGE:
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
            if dist < SCOUT_VIEW_RANGE:
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
        if dist < SCOUT_CRUISE_ARRIVAED_RANGE:
            return True
        else:
            return False

    def _check_in_monitor_range(self):
        dist = md.calculate_distance(self._scout.unit().float_attr.pos_x, 
                                     self._scout.unit().float_attr.pos_y,
                                     self._monitor_pos[0],
                                     self._monitor_pos[1])
        if dist < SCOUT_CRUISE_ARRIVAED_RANGE:
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
        if ver == EXPLORE_V3:
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
        if dist < SCOUT_CRUISE_ARRIVAED_RANGE:
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
        pos3 = (pos2[0] - SCOUT_CRUISE_RANGE, pos2[1])
        pos4 = (home_x /3 + (target_x * 2) / 3, home_y / 3 + (target_y * 2) / 3)
        pos5 = (pos2[0] + SCOUT_CRUISE_RANGE, pos2[1])

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
            dist = md.calculate_distance(me[0], 
                                         me[1],
                                         unit.float_attr.pos_x,
                                         unit.float_attr.pos_y)
            if dist < SCOUT_CRUISE_RANGE:
                scout_armys.append(unit)
                break
        if len(scout_armys) > 0:
            alarm = sp.ScoutAlarm()
            alarm.enmey_armys = scout_armys
            if not spool.alarms.full():
                spool.alarms.put(alarm)


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
                    return self._move_to_target(self._circle_path[
                                                    self._cur_circle_target])
                else:
                    self._cur_circle_target = 0
                    return self._move_to_target(self._circle_path[
                                                    self._cur_circle_target])
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
                if enemy.float_attr.build_progress >= BUILD_PROGRESS_FINISH:
                    spawning_on = True
            else:
                pass

        me = (self._scout.unit().float_attr.pos_x, 
              self._scout.unit().float_attr.pos_y)

        scout_armys = []
        for unit in armys:
            dist = md.calculate_distance(me[0], 
                                         me[1],
                                         unit.float_attr.pos_x,
                                         unit.float_attr.pos_y)
            if dist < SCOUT_CRUISE_RANGE:
                scout_armys.append(unit)
        if len(eggs) > 0 and spawning_on:
           #print("SCOUT escape, may be zergling is building")
           return True

        if len(scout_armys) > 0:
            return True
        else:
            return False


class ScoutEnemyTask(ScoutTask):
    def __init__(self, scout, home, target):
        super(ScoutEnemyTask, self).__init__(scout, home)
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

        if self._cur_step == ForcedScoutStep.STEP_INIT:
            # step one, move to target base
            action = self._move_to_target(self._target.pos)
            self._cur_step = ForcedScoutStep.STEP_MOVE_TO_BASE
            return action
        elif self._cur_step == ForcedScoutStep.STEP_MOVE_TO_BASE:
            # step two, circle target base
            if self._arrive_xy(self.scout().unit(), self._target.pos[0],
                    self._target.pos[1], 5) or self._detect_enemy(view_enemys):
                self._cur_step = ForcedScoutStep.STEP_RETREAT
                return self._move_to_home()
            else:
                return None
        elif self._cur_step == ForcedScoutStep.STEP_RETREAT:
            # step three, retreat
            if self._arrive_xy(self.scout().unit(),
                               self._home[0], self._home[1], 10):
                self._status = md.ScoutTaskStatus.DONE

            return None

    def _arrive_xy(self, u, target_x, target_y, error):
        x = u.float_attr.pos_x - target_x
        y = u.float_attr.pos_y - target_y
        distance = (x * x + y * y) ** 0.5

        return distance < error

    def distance(self, pos1, pos2):
        x = pos1[0] - pos2[0]
        y = pos1[1] - pos2[1]

        return (x * x + y * y) ** 0.5

    def _detect_enemy(self, view_enemys):
        scout = self.scout().unit()
        scout_pos = [scout.float_attr.pos_x, scout.float_attr.pos_y]

        for enemy in view_enemys:
            enemy_pos = [enemy.float_attr.pos_x, enemy.float_attr.pos_y]

            if self.distance(enemy_pos, scout_pos) < 8:
                #print('distance < 8')
                return True

        return False
