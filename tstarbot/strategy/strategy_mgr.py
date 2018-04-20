"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
from enum import Enum

from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID
from tstarbot.strategy.squad import Squad
from tstarbot.strategy.squad import SquadStatus
from tstarbot.strategy.army import Army
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.queue.combat_command_queue import CombatCommand
from tstarbot.strategy.renderer import StrategyRenderer

Strategy = Enum('Strategy', ('RUSH', 'ECONOMY_FIRST', 'ONEWAVE', 'REFORM'))


class BaseStrategyMgr(object):

    def __init__(self):
        self.rally_set_dict = {}

    def reset(self):
        self.rally_set_dict = {}

    def update(self, dc, am):
        pass


class ZergStrategyMgr(BaseStrategyMgr):

    def __init__(self):
        super(ZergStrategyMgr, self).__init__()
        self._enable_render = False
        self._strategy = Strategy.REFORM
        self._army = Army()
        self._cmds = []
        self._ready_to_go = False
        self._ready_to_attack = False
        self._rally_pos = None
        self._rally_pos_for_attack = None
        self._trigger_army_size = 20
        if self._enable_render:
            self._renderer = StrategyRenderer(window_size=(480, 360),
                                              world_size={'x': 200, 'y': 150},
                                              caption='SC2: Strategy Viewer')

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._army.update(dc.dd.combat_pool)
        self._dc = dc
        self._update_config(dc)

        self._command_army(dc.dd.combat_command_queue)

        if self._enable_render:
            self._renderer.draw(squads=self._army.squads,
                                enemy_clusters=dc.dd.enemy_pool.enemy_clusters,
                                commands=self._cmds)
            self._renderer.render()

    def reset(self):
        self._army = Army()
        self._ready_to_go = False
        self._ready_to_attack = False
        self._rally_pos = None
        self._rally_pos_for_attack = None
        self._trigger_army_size = 20
        if self._enable_render:
            self._renderer = list()

    def _update_config(self, dc):
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
                else:
                    raise ValueError('Combat strategy [%s] is not supported.' % dc.config.combat_strategy)

    def _organize_army_by_size(self, size):
        # self._create_fixed_size_squads(size)
        # TODO(pengsun): use config for the organizing logic?
        unit_type_blacklist = {
            UNIT_TYPEID.ZERG_QUEEN.value
        }
        self._create_fixed_size_spec_type_squads(size, unit_type_blacklist)

    def _create_fixed_size_squads(self, squad_size):
        while len(self._army.unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, squad_size))

    def _create_fixed_size_spec_type_squads(self, squad_size,
                                            unit_type_blacklist=set()):
        allowed_unsquaded_units = [u for u in self._army.unsquaded_units if
                                   u.unit.unit_type not in unit_type_blacklist]
        while len(allowed_unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(allowed_unsquaded_units, squad_size))
            allowed_unsquaded_units = [
                u for u in self._army.unsquaded_units
                if u.unit.unit_type not in unit_type_blacklist
            ]

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
            if (squad.status == SquadStatus.IDLE or
                squad.status == SquadStatus.MOVE):
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

    def _command_army_reform(self, cmd_queue):
        enemy_pool = self._dc.dd.enemy_pool

        # rally after production
        if not self._ready_to_go:
            if enemy_pool.closest_cluster is None:
                return None
            self._rally_pos = self._find_base_pos_in_danger(enemy_pool)
            if self._rally_pos is None:
                return None
            for squad in self._army.squads:
                squad.status = SquadStatus.MOVE
                cmd = CombatCommand(
                    type=CombatCmdType.RALLY,
                    squad=squad,
                    position=self._rally_pos)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

            rallied_squads = [squad for squad in self._army.squads
                              if self._distance(squad.centroid, self._rally_pos) < 8]
            for squad in rallied_squads:
                squad.status = SquadStatus.IDLE
            if len(rallied_squads) >= self._trigger_army_size:
                self._ready_to_go = True

        # rally before attack
        if self._ready_to_go and not self._ready_to_attack:
            if enemy_pool.weakest_cluster is None:
                return None
            temp_pos = enemy_pool.closest_cluster.centroid
            for squad in self._army.squads:
                if self._distance(squad.centroid,
                                  enemy_pool.closest_cluster.centroid) < 30:  # safe dist
                    self._rally_pos_for_attack = squad.centroid
            for squad in self._army.squads:
                squad.status = SquadStatus.MOVE
                cmd = CombatCommand(
                    type=CombatCmdType.RALLY,
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
                squad.status = SquadStatus.IDLE

            if len(rallied_squads_for_attack) >= self._trigger_army_size - 5:
                self._ready_to_attack = True

        # attack
        if self._ready_to_attack:
            if enemy_pool.weakest_cluster is None:
                return None
            if self._army.num_hydralisk_units + self._army.num_roach_units < 10:
                self._ready_to_attack = False
                self._ready_to_go = False
                # self._trigger_army_size = 30
                return None
            for squad in self._army.squads:
                squad.status = SquadStatus.ATTACK
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

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
