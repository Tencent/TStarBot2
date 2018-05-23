"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import numpy as np
from enum import Enum

from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID
from tstarbot.strategy.squad import Squad
from tstarbot.strategy.squad import SquadStatus, MutaliskSquadStatus
from tstarbot.strategy.army import Army
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.queue.combat_command_queue import CombatCommand
from tstarbot.strategy.renderer import StrategyRenderer
from tstarbot.data.pool.macro_def import COMBAT_ATTACK_UNITS, COMBAT_FLYING_UNITS
from tstarbot.data.pool.macro_def import COMBAT_UNITS, COMBAT_UNITS_FOOD_DICT, BUILDING_UNITS
from tstarbot.data.pool.map_tool import get_slopes


Strategy = Enum('Strategy', ('RUSH', 'ECONOMY_FIRST', 'ONEWAVE', 'REFORM', 'HARASS'))
UNIT_BLACKLIST = {
    UNIT_TYPEID.ZERG_QUEEN.value,
    UNIT_TYPEID.ZERG_MUTALISK.value,
    UNIT_TYPEID.ZERG_ZERGLING.value
}


class BaseStrategyMgr(object):

    def __init__(self, dc):
        self.rally_set_dict = {}

    def reset(self):
        self.rally_set_dict = {}

    def update(self, dc, am):
        pass


class ZergStrategyMgr(BaseStrategyMgr):

    def __init__(self, dc):
        super(ZergStrategyMgr, self).__init__(dc)
        self._enable_render = False
        self._strategy = Strategy.HARASS
        self._army = Army()
        self._cmds = []
        self._ready_to_go = False
        self._ready_to_attack = False
        self._mutalisk_ready_to_go = False
        self._mutalisk_ready_to_harass = False
        self._food_trigger = 100

        self._rally_pos = None
        self._rally_pos_for_attack = None
        self._verbose = 0
        if self._enable_render:
            self._renderer = StrategyRenderer(window_size=(480, 360),
                                              world_size={'x': 200, 'y': 150},
                                              caption='SC2: Strategy Viewer')
        self._init_config(dc)
        self._global_step = 0
        self._slopes = None

    def reset(self):
        self._army = Army()
        self._ready_to_go = False
        self._ready_to_attack = False
        self._mutalisk_ready_to_go = False
        self._mutalisk_ready_to_harass = False
        self._food_trigger = 100

        self._rally_pos = None
        self._rally_pos_for_attack = None
        if self._enable_render:
            self._renderer = list()
        self._global_step = 0
        self._slopes = None

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._army.update(dc.dd.combat_pool)
        self._dc = dc
        if self._global_step == 1:
            self._slopes = get_slopes(dc.sd.timestep)

        self._command_army(dc.dd.combat_command_queue)

        if self._enable_render:
            self._renderer.draw(squads=self._army.squads,
                                enemy_clusters=dc.dd.enemy_pool.enemy_clusters,
                                commands=self._cmds)
            self._renderer.render()
        self._global_step += 1

    def _init_config(self, dc):
        if hasattr(dc, 'config'):
            if hasattr(dc.config, 'combat_strategy'):
                if dc.config.combat_strategy == 'RUSH':
                    self._strategy = Strategy.RUSH
                elif dc.config.combat_strategy == 'ECONOMY_FIRST':
                    self._strategy = Strategy.ECONOMY_FIRST
                elif dc.config.combat_strategy == 'ONEWAVE':
                    self._strategy = Strategy.ONEWAVE
                elif dc.config.combat_strategy == 'REFORM':
                    self._strategy = Strategy.REFORM
                elif dc.config.combat_strategy == 'HARASS':
                    self._strategy = Strategy.HARASS
                else:
                    raise ValueError('Combat strategy [%s] is not supported.' % dc.config.combat_strategy)

    def _organize_army_by_size(self, size):
        # self._create_fixed_size_squads(size)
        # self._create_fixed_size_zergling_squads(squad_size=4, uniform='stone', unique=True)
        self._create_fixed_size_spec_type_squads(size, UNIT_BLACKLIST)
        self._create_fixed_size_mutalisk_squads(squad_size=3, mutalisk_uniform='main_base', unique=True)
        self._create_fixed_size_mutalisk_squads(squad_size=3, mutalisk_uniform='sub_base1', unique=True)
        self._create_fixed_size_mutalisk_squads(squad_size=3, mutalisk_uniform='sub_base2', unique=True)

    def _organize_army_by_type(self, squad_size):
        units_by_type = {}
        for u in self._army.unsquaded_units:
            if u.unit.unit_type in UNIT_BLACKLIST:
                continue
            if u.unit.unit_type in units_by_type.keys():
                units_by_type[u.unit.unit_type].append(u)
            else:
                units_by_type[u.unit.unit_type] = [u]
        for k in units_by_type.keys():
            uu = units_by_type[k]
            while len(uu) >= squad_size:
                s = random.sample(uu, squad_size)
                for u in s:
                    uu.remove(u)
                self._army.create_squad(s)
            if len(uu) > 0:
                self._army.create_squad(uu)

    def _organize_army_by_airforce(self, squad_size):
        units_by_fly = [[], []]  # can fly, cannot fly
        for u in self._army.unsquaded_units:
            if u.unit.unit_type in UNIT_BLACKLIST:
                continue
            if u.unit.unit_type in COMBAT_FLYING_UNITS:
                units_by_fly[0].append(u)
            else:
                units_by_fly[1].append(u)
        for k in range(2):
            uu = units_by_fly[k]
            while len(uu) >= squad_size:
                s = random.sample(uu, squad_size)
                for u in s:
                    uu.remove(u)
                self._army.create_squad(s)
            if len(uu) > 0:
                self._army.create_squad(uu)

    def _create_fixed_size_squads(self, squad_size):
        while len(self._army.unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, squad_size))

    def _create_fixed_size_spec_type_squads(self, squad_size, unit_type_blacklist=set()):
        allowed_unsquaded_units = [u for u in self._army.unsquaded_units if
                                   u.unit.unit_type not in unit_type_blacklist]
        while len(allowed_unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(allowed_unsquaded_units, squad_size))
            allowed_unsquaded_units = [
                u for u in self._army.unsquaded_units
                if u.unit.unit_type not in unit_type_blacklist
            ]

    def _create_fixed_size_mutalisk_squads(self, squad_size, mutalisk_uniform, unique=False):
        if unique:
            squads = [s for s in self._army.squads]
            if mutalisk_uniform in [s.uniform for s in squads]:
                return None
        unsquaded_mutalisks = [u for u in self._army.unsquaded_units if
                              u.unit.unit_type == UNIT_TYPEID.ZERG_MUTALISK.value]
        while len(unsquaded_mutalisks) >= squad_size:
            print('create mutalisk squad: ' + mutalisk_uniform)
            self._army.create_squad(
                random.sample(unsquaded_mutalisks, squad_size), mutalisk_uniform)
            unsquaded_mutalisks = [
                u for u in self._army.unsquaded_units
                if u.unit.unit_type == UNIT_TYPEID.ZERG_MUTALISK.value]

    def _create_fixed_size_zergling_squads(self, squad_size, uniform, unique=False):
        if unique:
            squads = [s for s in self._army.squads]
            if uniform in [s.uniform for s in squads]:
                return None
        unsquaded_zerglings = [u for u in self._army.unsquaded_units if
                               u.unit.unit_type == UNIT_TYPEID.ZERG_ZERGLING.value]
        while len(unsquaded_zerglings) >= squad_size:
            print('create zerglings squad: ' + uniform)
            self._army.create_squad(
                random.sample(unsquaded_zerglings, squad_size), uniform)
            unsquaded_zerglings = [
                u for u in self._army.unsquaded_units
                if u.unit.unit_type == UNIT_TYPEID.ZERG_ZERGLING.value]

    def _create_queen_squads(self):
        queens = [u for u in self._army.unsquaded_units
                  if u.unit.unit_type == UNIT_TYPEID.ZERG_QUEEN.value]
        return Squad(queens)

    def _command_army(self, cmd_queue):
        self._cmds = list()
        if self._strategy == Strategy.RUSH:
            self._organize_army_by_size(size=8)
            self._command_army_rush(cmd_queue)
        elif self._strategy == Strategy.ECONOMY_FIRST:
            self._organize_army_by_size(size=8)
            self._command_army_economy_first(cmd_queue)
        elif self._strategy == Strategy.ONEWAVE:
            self._organize_army_by_size(size=8)
            self._command_army_onewave(cmd_queue)
        elif self._strategy == Strategy.REFORM:
            self._organize_army_by_size(size=1)
            self._command_army_defend(cmd_queue)
            self._command_army_reform(cmd_queue)
        elif self._strategy == Strategy.HARASS:
            self._organize_army_by_size(size=1)
            self._command_army_harass(cmd_queue)
            if not self._command_army_defend(cmd_queue):
                self._command_army_reform(cmd_queue)

    def _command_army_rush(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool
        if len(self._army.squads) >= 1 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def _command_army_economy_first(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool
        if len(self._army.squads) >= 5 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def _command_army_onewave(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool

        # rally
        if self._rally_pos is None:
            self._rally_pos = self._get_rally_pos()
        for squad in self._army.squads:
            if squad.status == SquadStatus.IDLE or squad.status == SquadStatus.MOVE:
                squad.status = SquadStatus.MOVE
                cmd = CombatCommand(
                    type=CombatCmdType.MOVE,
                    squad=squad,
                    position=self._rally_pos)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

        # attack
        rallied_squads = [squad for squad in self._army.squads
                          if self._distance(squad.centroid, self._rally_pos) < 8]
        if not self._ready_to_go and len(rallied_squads) >= 4:
            self._ready_to_go = True
        if self._ready_to_go and enemy_pool.weakest_cluster is not None:
            attacking_squads = [squad for squad in self._army.squads
                                if squad.status == SquadStatus.ATTACK]
            for squad in rallied_squads + attacking_squads:
                squad.status = SquadStatus.ATTACK
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def _command_army_defend(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool
        enemy_combat_units = self._find_enemy_combat_units(enemy_pool.units)
        if len(enemy_combat_units) == 0 or enemy_pool.closest_cluster is None:
            return False
        bases = self._dc.dd.base_pool.bases

        if len(bases) > 2:
            enemy_attacking_me = False
            for tag in bases:
                b = bases[tag].unit
                for e in enemy_combat_units:
                    if self._cal_square_dist(e, b) < 30:
                        enemy_attacking_me = True
                        closest_enemy = e
                        break
                if enemy_attacking_me:
                    break

            if enemy_attacking_me:
                print('Defend.')
                for squad in self._army.squads + [self._create_queen_squads()]:
                    if squad.uniform is not None and \
                            squad.combat_status not in [MutaliskSquadStatus.IDLE,
                                                        MutaliskSquadStatus.PHASE1]:
                        continue
                    if squad.status == SquadStatus.SCOUT:
                        continue
                    squad.status = SquadStatus.MOVE
                    cmd = CombatCommand(
                        type=CombatCmdType.ATTACK,
                        squad=squad,
                        position={
                            'x': closest_enemy.float_attr.pos_x,
                            'y': closest_enemy.float_attr.pos_y
                        })
                    cmd_queue.push(cmd)
                    self._cmds.append(cmd)
                return True
        else:
            enemy_attacking_me = False
            for tag in bases:
                b = bases[tag].unit
                for e in enemy_combat_units:
                    if self._cal_square_dist(e, b) < 60:
                        enemy_attacking_me = True
                        # closest_enemy = e
                        break
                if enemy_attacking_me:
                    break

            if enemy_attacking_me:
                print('Defend rush.')
                for squad in self._army.squads + [self._create_queen_squads()]:
                    if squad.uniform is not None and \
                            squad.combat_status not in [MutaliskSquadStatus.IDLE,
                                                        MutaliskSquadStatus.PHASE1]:
                        continue
                    if squad.status == SquadStatus.SCOUT:
                        continue
                    squad.status = SquadStatus.MOVE

                    second_base_pos = self._get_second_base_pos()
                    defend_base_pos = self._get_main_base_pos() if second_base_pos is None else second_base_pos

                    cmd = CombatCommand(
                        type=CombatCmdType.ATTACK,
                        squad=squad,
                        position=self._get_slope_up_pos(defend_base_pos)
                    )
                    cmd_queue.push(cmd)
                    self._cmds.append(cmd)
                return True

        return False

    def _command_army_reform(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool

        # rally after production
        if not self._ready_to_go:
            if enemy_pool.closest_cluster is None:
                return None
            if self._verbose > 0:
                print('rally')
            self._rally_pos = self._find_base_pos_in_danger(enemy_pool)
            if self._rally_pos is None:
                return None
            for squad in self._army.squads:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                squad.status = SquadStatus.MOVE

                cmd = CombatCommand(
                    type=CombatCmdType.MOVE,  # if self.estimate_self_army_power_in_battle() < 0 else CombatCmdType.MOVE,
                    squad=squad,
                    position=self._rally_pos)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

            rallied_squads = [squad for squad in self._army.squads
                              if self._distance(squad.centroid, self._rally_pos) < 10]
            for squad in rallied_squads:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                squad.status = SquadStatus.IDLE
            # print('food: {}, go: {}'.format(self._dc.sd.obs['player'][3], self._food_trigger))
            if self._dc.sd.obs['player'][3] >= self._food_trigger and \
                    len(rallied_squads) >= 15:
                self._ready_to_go = True

        # rally before attack
        attack_pos = enemy_pool.priority_pos
        if attack_pos is None:
            if enemy_pool.closest_cluster is None:
                return None
            attack_pos = enemy_pool.closest_cluster.centroid

        if self._ready_to_go and not self._ready_to_attack:
            if enemy_pool.closest_cluster is None:
                return None
            if self._verbose > 0:
                print('ready to go and rally before attack')

            temp_pos = attack_pos
            for squad in self._army.squads:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                if 25 < self._distance(squad.centroid,
                                       enemy_pool.closest_cluster.centroid) < 30:  # safe dist
                    self._rally_pos_for_attack = squad.centroid

            # # fix rally pos
            # base_pool = self._dc.dd.base_pool
            # if list(base_pool.bases.values())[0].unit.float_attr.pos_x < list(base_pool.bases.values())[0].unit.float_attr.pos_y:
            #     self._rally_pos_for_attack = {'x': 110, 'y': 48}
            # else:
            #     self._rally_pos_for_attack = {'x': 60, 'y': 90}
            if (self._dc.sd.obs['player'][5] < self.estimate_enemy_army_power()
                    and self._dc.sd.obs['player'][3] < 195):
                self._ready_to_go = False
                self._food_trigger += 20
                self._food_trigger = min(self._food_trigger, 195)

            for squad in self._army.squads:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                squad.status = SquadStatus.MOVE
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=temp_pos if self._rally_pos_for_attack is None
                    else self._rally_pos_for_attack)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

            rallied_squads_for_attack = [squad for squad in self._army.squads
                                         if self._distance(squad.centroid,
                                                           self._rally_pos_for_attack) < 8] \
                if (self._rally_pos_for_attack is not None) else []
            for squad in rallied_squads_for_attack:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                squad.status = SquadStatus.IDLE

            if len(rallied_squads_for_attack) >= 15:
                # print('rally pos: ', self._rally_pos_for_attack)
                self._ready_to_attack = True

        # attack
        if self._ready_to_attack:
            if enemy_pool.closest_cluster is None:
                return None
            if self._verbose > 0:
                print('attack')
            # print('army food me: {}, enemy: {}'.format(self._dc.sd.obs['player'][5], self.estimate_enemy_army_power()))
            est_enemy_power = self.estimate_enemy_army_power()
            # print('battle self power: ', self.estimate_self_army_power_in_battle(), 'enemy: ', est_enemy_power)
            if (self._dc.sd.obs['player'][5] < est_enemy_power
                    and self._dc.sd.obs['player'][3] < 195):
                self._ready_to_attack = False
                self._ready_to_go = False
                self._food_trigger += 20
                self._food_trigger = min(self._food_trigger, 195)
                return None
            for squad in self._army.squads:
                if squad.uniform is not None:
                    continue
                if squad.status == SquadStatus.SCOUT:
                    continue
                squad.status = SquadStatus.ATTACK
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=attack_pos)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def estimate_enemy_army_power(self):
        enemy_combat_units = [u for u in self._dc.dd.enemy_pool.units if u.int_attr.unit_type in COMBAT_UNITS]
        enemy_army_food = 0
        for e in enemy_combat_units:
            if e.int_attr.unit_type not in COMBAT_UNITS_FOOD_DICT.keys():
                continue
            enemy_army_food += COMBAT_UNITS_FOOD_DICT[e.int_attr.unit_type]
        return enemy_army_food

    def estimate_self_army_power_in_battle(self):
        enemy_combat_units = [u for u in self._dc.dd.enemy_pool.units if u.int_attr.unit_type in COMBAT_UNITS]
        if len(enemy_combat_units) == 0:
            return -1
        self_combat_units = [u.unit for u in self._dc.dd.combat_pool.units
                             if u.unit.int_attr.unit_type != UNIT_TYPEID.ZERG_MUTALISK.value]  # do not include mutalisk
        battle_pos = None
        for e in enemy_combat_units:
            for u in self_combat_units:
                if self._cal_square_dist(u, e) < 30:
                    battle_pos = {'x': u.float_attr.pos_x,
                                  'y': u.float_attr.pos_y}

        if battle_pos is None:
            return -1

        self_combat_units_in_battle = [u for u in self_combat_units
                                       if self._distance({'x': u.float_attr.pos_x,
                                                          'y': u.float_attr.pos_y}, battle_pos) < 10]
        self_army_food_in_battle = 0
        for u in self_combat_units_in_battle:
            if u.int_attr.unit_type not in COMBAT_UNITS_FOOD_DICT.keys():
                continue
            self_army_food_in_battle += COMBAT_UNITS_FOOD_DICT[u.int_attr.unit_type]
        return self_army_food_in_battle

    def _command_army_harass(self, cmd_queue):
        # if has mutalisk -> harass
        self._get_mutalisk_safe_pos()
        self._mutalisk_harass(cmd_queue, 'main_base',
                              self.safe_mutalisk_safe_pos1,
                              self.safe_mutalisk_safe_pos2)
        # self._mutalisk_harass(cmd_queue, 'sub_base1',
        #                      self.safe_mutalisk_safe_pos3,
        #                      self.safe_mutalisk_safe_pos4)
        self._mutalisk_harass(cmd_queue, 'sub_base1',
                              self.safe_mutalisk_safe_pos5,
                              self.safe_mutalisk_safe_pos6)

    # def _command_army_atk_stone(self, cmd_queue, uniform='stone'):
    #     stones = [u for u in self._dc.sd.obs['units']
    #               if u.int_attr.unit_type == UNIT_TYPEID.]
    #     for squad in self._army.squads:
    #         if squad.uniform == uniform:
    #             cmd = CombatCommand(
    #                     type=CombatCmdType.MOVE,
    #                     squad=squad,
    #                     position=harass_station_pos2)
    #             cmd_queue.push(cmd)
    #             self._cmds.append(cmd)

    def _mutalisk_harass(self, cmd_queue, mutalisk_uniform,
                         harass_station_pos1, harass_station_pos2):
        enemy_units = self._dc.dd.enemy_pool.units
        enemy_buildings_and_drones_overlords = [e for e in enemy_units
                                                if e.int_attr.unit_type in BUILDING_UNITS or
                                                e.int_attr.unit_type in [UNIT_TYPEID.ZERG_OVERLORD.value,
                                                                         UNIT_TYPEID.ZERG_DRONE.value,
                                                                         UNIT_TYPEID.ZERG_OVERSEER.value]
                                                ]

        for squad in self._army.squads:
            if squad.uniform == mutalisk_uniform and squad.combat_status == MutaliskSquadStatus.IDLE:
                # rally at a safe corner
                cmd = CombatCommand(
                        type=CombatCmdType.ATTACK,  # for defend
                        squad=squad,
                        position=harass_station_pos1)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

        rallied_mutalisk_squads = [squad for squad in self._army.squads
                                   if squad.uniform == mutalisk_uniform and
                                   self._distance(squad.centroid, harass_station_pos1) < 5]
        if len(rallied_mutalisk_squads) > 0:
            rallied_mutalisk_squads[0].combat_status = MutaliskSquadStatus.PHASE1

        for squad in self._army.squads:
            if squad.uniform == mutalisk_uniform and squad.combat_status == MutaliskSquadStatus.PHASE1:
                cmd = CombatCommand(
                        type=CombatCmdType.MOVE,
                        squad=squad,
                        position=harass_station_pos2)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

        rallied_mutalisk_squads = [squad for squad in self._army.squads
                                   if squad.uniform == mutalisk_uniform and
                                   self._distance(squad.centroid, harass_station_pos2) < 5]
        if len(rallied_mutalisk_squads) > 0:
            rallied_mutalisk_squads[0].combat_status = MutaliskSquadStatus.PHASE2

        if len(enemy_buildings_and_drones_overlords) == 0:
            return None
        for squad in self._army.squads:
            if squad.uniform == mutalisk_uniform and squad.combat_status == MutaliskSquadStatus.PHASE2:
                closest_enemy_base = self._find_closest_enemy_to_pos(squad.centroid, enemy_buildings_and_drones_overlords)
                cmd = CombatCommand(
                        type=CombatCmdType.ATTACK,
                        squad=squad,
                        position={'x': closest_enemy_base.float_attr.pos_x,
                                  'y': closest_enemy_base.float_attr.pos_y})
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def _get_mutalisk_safe_pos(self):
        base_pool = self._dc.dd.base_pool
        if len(list(base_pool.bases.values())) > 0:
            base_rand = list(base_pool.bases.values())[0].unit
        else:
            return {'x': 0, 'y': 0}
        if base_rand.float_attr.pos_x > base_rand.float_attr.pos_y:
            self.safe_mutalisk_safe_pos1 = {'x': 20, 'y': 5}
            self.safe_mutalisk_safe_pos2 = {'x': 20, 'y': 140}

            self.safe_mutalisk_safe_pos3 = {'x': 20, 'y': 5}
            self.safe_mutalisk_safe_pos4 = {'x': 20, 'y': 75}

            self.safe_mutalisk_safe_pos5 = {'x': 180, 'y': 140}
            self.safe_mutalisk_safe_pos6 = {'x': 100, 'y': 140}
        else:
            self.safe_mutalisk_safe_pos1 = {'x': 180, 'y': 140}
            self.safe_mutalisk_safe_pos2 = {'x': 180, 'y': 5}

            self.safe_mutalisk_safe_pos3 = {'x': 180, 'y': 140}
            self.safe_mutalisk_safe_pos4 = {'x': 180, 'y': 75}

            self.safe_mutalisk_safe_pos5 = {'x': 20, 'y': 5}
            self.safe_mutalisk_safe_pos6 = {'x': 100, 'y': 5}

    def _get_rally_pos(self):
        base_pool = self._dc.dd.base_pool
        if list(base_pool.bases.values())[0].unit.float_attr.pos_x < 44:
            return {'x': 50.5, 'y': 60.5}
        else:
            return {'x': 37.5, 'y': 27.5}

    def _distance(self, pos_a, pos_b):
        return ((pos_a['x'] - pos_b['x']) ** 2 + \
                (pos_a['y'] - pos_b['y']) ** 2) ** 0.5

    def _find_base_pos_in_danger(self, enemy_pool):
        bases = self._dc.dd.base_pool.bases
        d_min = 10000
        pos = None
        for tag in bases:
            base_pos = {'x': bases[tag].unit.float_attr.pos_x,
                        'y': bases[tag].unit.float_attr.pos_y}
            d = self._distance(base_pos,
                               enemy_pool.closest_cluster.centroid)
            if d < d_min:
                d_min = d
                pos = base_pos
        return pos

    def _find_closest_base_to_enemy(self, enemy_pool):
        bases = self._dc.dd.base_pool.bases
        d_min = 10000
        target_base = None
        for tag in bases:
            base_pos = {'x': bases[tag].unit.float_attr.pos_x,
                        'y': bases[tag].unit.float_attr.pos_y}
            d = self._distance(base_pos,
                               enemy_pool.closest_cluster.centroid)
            if d < d_min:
                d_min = d
                target_base = bases[tag].unit
        return target_base

    def _find_closest_enemy(self, u, enemies):
        dist = []
        for e in enemies:
            dist.append(self._cal_square_dist(u, e))
        idx = np.argmin(dist)
        return enemies[idx]

    @staticmethod
    def _find_enemy_combat_units(emeny_units):
        enemy_combat_units = []
        for u in emeny_units:
            if u.int_attr.unit_type in COMBAT_UNITS:
                enemy_combat_units.append(u)
        return enemy_combat_units

    @staticmethod
    def _cal_square_dist(u1, u2):
        return pow(pow(u1.float_attr.pos_x - u2.float_attr.pos_x, 2) +
                   pow(u1.float_attr.pos_y - u2.float_attr.pos_y, 2), 0.5)

    def _find_closest_enemy_to_pos(self, pos, enemies):
        dist = []
        for e in enemies:
            e_pos = {'x': e.float_attr.pos_x,
                     'y': e.float_attr.pos_y}
            dist.append(self._distance(pos, e_pos))
        idx = np.argmin(dist)
        return enemies[idx]

    @staticmethod
    def _get_center_of_units(units):
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

    def _get_main_base_pos(self):
        return {'x': self._dc.dd.base_pool.home_pos[0],
                'y': self._dc.dd.base_pool.home_pos[1]}

    def _get_second_base_pos(self):
        bases = self._dc.dd.base_pool.bases
        if len(bases) < 2:
            return None
        min_dist = 100000
        second_base_pos = None
        for tag in bases:
            area = bases[tag].resource_area
            d = self._dc.dd.base_pool.home_dist[area]
            if 0.1 < d < min_dist:
                min_dist = d
                second_base_pos = area.ideal_base_pos
        return {'x': second_base_pos[0],
                'y': second_base_pos[1]}

    def _get_slope_to_xy(self, xy):
        if self._slopes is None:
            return None
        min_dist = 100000
        target_slope = None
        for s in self._slopes:
            d = self._distance({'x': s.x, 'y': s.y}, xy)
            if d < min_dist:
                min_dist = d
                target_slope = s
        return target_slope

    def _get_slope_up_pos(self, base_pos):
        slope = self._get_slope_to_xy(base_pos)
        max_height = max(slope.height)
        highest_pos = [pos for pos, h in zip(slope.pos, slope.height) if h == max_height]
        target_pos = np.mean(highest_pos, axis=0)
        offset_x = base_pos['x'] - target_pos[0]
        offset_y = base_pos['y'] - target_pos[1]
        x = target_pos[0] + 0.3 * offset_x
        y = target_pos[1] + 0.3 * offset_y
        return {'x': x, 'y': y}
