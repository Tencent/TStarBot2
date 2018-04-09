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

Strategy = Enum('Strategy', ('RUSH', 'ECONOMY_FIRST', 'ONEWAVE'))


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
        self._strategy = Strategy.ONEWAVE
        self._army = Army()
        self._cmds = []
        self._onewave_triggered = False
        self._rally_pos = None
        if self._enable_render:
            self._renderer = StrategyRenderer(window_size=(480, 360),
                                              world_size={'x': 200, 'y': 150},
                                              caption='SC2: Strategy Viewer')

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._army.update(dc.dd.combat_pool)
        self._dc = dc

        self._organize_army_by_size()
        self._command_army(dc.dd.combat_command_queue)

        if self._enable_render:
            self._renderer.draw(squads=self._army.squads,
                                enemy_clusters=dc.dd.enemy_pool.enemy_clusters,
                                commands=self._cmds)
            self._renderer.render()

    def reset(self):
        self._army = Army()
        self._onewave_triggered = False
        self._rally_pos = None
        if self._enable_render:
            self._renderer.clear()

    def _organize_army_by_size(self):
        self._create_fixed_size_squads(8)

    def _create_fixed_size_squads(self, squad_size):
        while len(self._army.unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, squad_size))

    def _command_army(self, cmd_queue):
        self._cmds.clear()
        if self._strategy == Strategy.RUSH:
            self._command_army_rush(cmd_queue)
        elif self._strategy == Strategy.ECONOMY_FIRST:
            self._command_army_economy_first(cmd_queue)
        else:
            self._command_army_onewave(cmd_queue)

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
        if not self._onewave_triggered and len(rallied_squads) >= 4:
            self._onewave_triggered = True
        if self._onewave_triggered and enemy_pool.weakest_cluster is not None:
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

    def _get_rally_pos(self):
        base_pool = self._dc.dd.base_pool
        if list(base_pool.bases.values())[0].unit.float_attr.pos_x < 44:
            return {'x': 45, 'y': 66}
        else:
            return {'x': 44, 'y': 25}

    def _distance(self, pos_a, pos_b):
        return ((pos_a['x'] - pos_b['x']) ** 2 + \
                (pos_a['y'] - pos_b['y']) ** 2) ** 0.5
