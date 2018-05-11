import math
import numpy as np

from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import ABILITY_ID
from tstarbot.data.pool.macro_def import COMBAT_ATTACK_UNITS, COMBAT_FLYING_UNITS


class MicroBase(object):
    """ Basic Micro Functions"""

    def __init__(self):
        self.roach_attack_range = 5
        self.dc = None
        self.self_combat_units = []
        self.enemy_units = []
        self.enemy_combat_units = []

    def reset(self):
        self.dc = None
        self.self_combat_units = []
        self.enemy_units = []
        self.enemy_combat_units = []

    def update(self, dc):
        self.dc = dc
        self.enemy_units = dc.dd.enemy_pool.units
        self.enemy_combat_units = self.find_enemy_combat_units(self.enemy_units)
        self.self_combat_units = [u.unit for u in dc.dd.combat_pool.units]

    @staticmethod
    def collect_units(units, unit_type, alliance=1):
        return [u for u in units
                if u.unit_type == unit_type and u.int_attr.alliance == alliance]

    @staticmethod
    def set_default_combat_rally(hatcheries, pos):
        actions = []
        for hatchery in hatcheries:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = ABILITY_ID.RALLY_UNITS.value
            action.action_raw.unit_command.target_world_space_pos.x = pos[0]
            action.action_raw.unit_command.target_world_space_pos.y = pos[1]
            action.action_raw.unit_command.unit_tags.append(hatchery.tag)
            actions.append(action)
        return actions

    @staticmethod
    def move_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.MOVE.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def move_dir(u, direction):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.MOVE.value
        action.action_raw.unit_command.target_world_space_pos.x = u.float_attr.pos_x + \
                                                                  direction[0] * 0.5
        action.action_raw.unit_command.target_world_space_pos.y = u.float_attr.pos_y + \
                                                                  direction[1] * 0.5
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def attack_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def attack_target(u, target):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def attack_target_by_tag(u, tag):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        action.action_raw.unit_command.target_unit_tag = tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def hold_fire(u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.HOLDPOSITION.value
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_closest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_closest_enemy(u, enemies=enemies)
        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def attack_weakest_enemy(self, u, enemies):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        target = self.find_weakest_enemy(enemies=enemies)
        action.action_raw.unit_command.target_unit_tag = target.tag
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def run_away_from_closest_enemy(u, closest_enemy_unit):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.SMART.value
        action.action_raw.unit_command.target_world_space_pos.x = u.float_attr.pos_x + \
            (u.float_attr.pos_x - closest_enemy_unit.float_attr.pos_x) * 0.2
        action.action_raw.unit_command.target_world_space_pos.y = u.float_attr.pos_y + \
            (u.float_attr.pos_y - closest_enemy_unit.float_attr.pos_y) * 0.2
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def find_closest_enemy(self, u, enemies):
        dist = []
        for e in enemies:
            dist.append(self.cal_square_dist(u, e))
        idx = np.argmin(dist)
        return enemies[idx]

    def find_closest_bases(self, u, bases):
        dist = []
        for b in bases:
            dist.append(self.cal_square_dist(u, b))
        idx = np.argmin(dist)
        return bases[idx]

    def find_closest_units_in_battle(self, self_units, e):
        dist = []
        for u in self_units:
            dist.append(self.cal_square_dist(u, e))
        idx = np.argmin(dist)
        return self_units[idx]

    @staticmethod
    def find_nearest_n_units(hatcheries, units, n):
        if len(hatcheries) == 0:
            return []
        hatchery = hatcheries[0]
        base_x = hatchery.float_attr.pos_x
        base_y = hatchery.float_attr.pos_y
        dists = []
        for m in units:
            x = m.float_attr.pos_x
            y = m.float_attr.pos_y
            dist = abs(x - base_x) + abs(y - base_y)
            dists.append(dist)
        idx = np.argsort(dists)
        selected_units = []
        for i in range(n):
            selected_units.append(units[idx[i]])
        return selected_units

    @staticmethod
    def find_units_wihtin_range(u, units, r=6):
        u_x = u.float_attr.pos_x
        u_y = u.float_attr.pos_y
        selected_units = []
        for m in units:
            x = m.float_attr.pos_x
            y = m.float_attr.pos_y
            dist = pow(pow(x - u_x, 2) + pow(y - u_y, 2), 0.5)
            if dist <= r:
                selected_units.append(m)
        return selected_units

    def find_weakest_nearby(self, u, units, dist):
        min_a = None
        min_hp = 10000
        for a in units:
            if self.cal_dist(u, a) < dist and 0 < a.float_attr.health < min_hp and self.can_atk(u, a):
                min_a = a
                min_hp = a.float_attr.health
        return min_a

    @staticmethod
    def find_weakest_enemy(enemies):
        hp = []
        for e in enemies:
            hp.append(e.float_attr.health)
        idx = np.argmin(hp)
        if hp[idx] == np.max(hp):
            idx = 0
        return enemies[idx]

    @staticmethod
    def find_strongest_unit_hp(units):
        hp = []
        for m in units:
            hp.append(m.float_attr.health / m.float_attr.health_max)
        max_hp = np.max(hp)
        return max_hp

    @staticmethod
    def find_enemy_combat_units(emeny_units):
        enemy_combat_units = []
        for u in emeny_units:
            if u.int_attr.unit_type in COMBAT_ATTACK_UNITS:
                enemy_combat_units.append(u)
        return enemy_combat_units

    def check_stronger_unit_front(self, u, ally_units, closest_enemy_unit):
        u_dist = self.cal_square_dist(u, closest_enemy_unit)
        for a in ally_units:
            if (self.cal_square_dist(a, closest_enemy_unit) < 0.8 * u_dist and
                            a.float_attr.health / a.float_attr.health_max > 0.95):
                return True
        return False

    def get_atk_range(self, unit_type):
        info = self.dc.sd.data_raw.units[unit_type]
        weapons = info.weapons
        if len(weapons) == 0:
            return None
        return weapons[0].range

    def get_atk_type(self, unit_type):
        info = self.dc.sd.data_raw.units[unit_type]
        weapons = info.weapons
        if len(weapons) == 0:
            return None
        return weapons[0].type # 1: Ground, 2: Air, 3: Any

    def can_fly(self, unit_type):
        if unit_type in COMBAT_FLYING_UNITS:
            return True
        else:
            return False

    def can_atk(self, src, dst):
        atk_type = self.get_atk_type(src.int_attr.unit_type)
        if not atk_type:
            return False
        if atk_type == 1:
            return not self.can_fly(dst.int_attr.unit_type)
        if atk_type == 2:
            return self.can_fly(dst.int_attr.unit_type)
        if atk_type == 3:
            return True
        raise NotImplementedError

    def ready_to_atk(self, u):
        return u.float_attr.weapon_cooldown < 2.0  # TODO: frame skip

    @staticmethod
    def cal_square_dist(u1, u2):
        return pow(pow(u1.float_attr.pos_x - u2.float_attr.pos_x, 2) +
                   pow(u1.float_attr.pos_y - u2.float_attr.pos_y, 2), 0.5)

    def cal_dist(self, u1, u2):
        return self.cal_square_dist(u1, u2) - u1.float_attr.radius - u2.float_attr.radius

    @staticmethod
    def cal_coor_dist(pos1, pos2):
        return pow(pow(pos1['x'] - pos2['x'], 2) +
                   pow(pos1['y'] - pos2['y'], 2), 0.5)

    @staticmethod
    def get_center_of_units(units):
        center_x = 0
        center_y = 0
        for u in units:
            center_x += u.float_attr.pos_x
            center_y += u.float_attr.pos_y
        if len(units) > 0:
            center_x /= len(units)
            center_y /= len(units)
        pos = {'x': center_x,
               'y': center_y}
        return pos

    def is_run_away_old(self, u, closest_enemy, self_combat_units):
        closest_enemy_dist = math.sqrt(self.cal_square_dist(u, closest_enemy))
        near_by_units = self.find_units_wihtin_range(u, self_combat_units, r=6)
        if (closest_enemy_dist < self.roach_attack_range and
            u.float_attr.health / u.float_attr.health_max < 0.3 and
                # not self.check_stronger_unit_front(u, near_by_units, closest_enemy_unit)):
                self.find_strongest_unit_hp(near_by_units) > 0.9):
            return True
        return False

    def is_run_away(self, u, closest_enemy, self_combat_units):
        closest_enemy_dist = self.cal_square_dist(u, closest_enemy)
        near_by_units = self.find_units_wihtin_range(u, self_combat_units, r=6)
        atk_range = self.get_atk_range(u.int_attr.unit_type)
        if atk_range and closest_enemy_dist < atk_range and \
            u.float_attr.health / u.float_attr.health_max < 0.3 and \
                self.find_strongest_unit_hp(near_by_units) > 0.9:
            return True
        return False
