"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
from enum import Enum

from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID
from tstarbot.strategy.squad import Squad
from tstarbot.strategy.army import Army
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.queue.combat_command_queue import CombatCommand
from tstarbot.strategy.renderer import StrategyRenderer

Strategy = Enum('Strategy', ('RUSH', 'ECONOMY_FIRST', 'WAVE'))


class BaseStrategyMgr(object):

    def __init__(self):
        self.rally_set_dict = {}

    def reset(self):
        self.rally_set_dict = {}

    def update(self, dc, am):
        pass

    def check_rally_set(self, hatcheries):
        for h in hatcheries:
            if h.tag not in self.rally_set_dict.keys() or not self.rally_set_dict[h.tag]:
                return False
        return True

    @staticmethod
    def collect_units(units, unit_type, alliance=1):
        return [u for u in units
                if u.unit_type == unit_type and u.int_attr.alliance == alliance]


class ZergStrategyMgr(BaseStrategyMgr):

    def __init__(self):
        super(ZergStrategyMgr, self).__init__()
        self._enable_render = False
        self._strategy = Strategy.RUSH
        self._dc = []
        self._army = Army()
        self._cmds = []
        self._support = True
        self._squad_size = 20
        if self._enable_render:
            self._renderer = StrategyRenderer(window_size=(480, 360),
                                              world_size={'x': 200, 'y': 150},
                                              caption='SC2: Strategy Viewer')

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._dc = dc
        self._army.update(dc.dd.combat_pool)

        self._organize_army_by_size()
        self._command_army(dc.dd.enemy_pool,
                           dc.dd.combat_command_queue)

        if self._enable_render:
            self._renderer.draw(squads=self._army.squads,
                                enemy_clusters=dc.dd.enemy_pool.enemy_clusters,
                                commands=self._cmds)
            self._renderer.render()

    def reset(self):
        self._army = Army()
        self._support = True
        self._squad_size = 20
        if self._enable_render:
            self._renderer.clear()

    def _organize_army_by_size(self):
        self._create_fixed_size_squads(self._squad_size)

    def _create_fixed_size_squads(self, squad_size):
        while len(self._army.unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, squad_size))

    def _command_army(self, enemy, cmd_queue):
        self._cmds.clear()
        if self._strategy == Strategy.RUSH:
            self._command_army_rush(enemy, cmd_queue)
        elif self._strategy == Strategy.ECONOMY_FIRST:
            self._command_army_economy_first(enemy, cmd_queue)

    def _command_army_rush(self, enemy_pool, cmd_queue):
        if len(self._army.squads) >= 1 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)

    def _command_army_economy_first(self, enemy_pool, cmd_queue):
        if len(self._army.squads) >= 5 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
                self._cmds.append(cmd)
