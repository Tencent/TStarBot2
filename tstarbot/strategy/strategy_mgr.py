"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
from enum import Enum

from tstarbot.strategy.squad import Squad
from tstarbot.strategy.army import Army
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.queue.combat_command_queue import CombatCommand


Strategy = Enum('Strategy', ('RUSH', 'ECONOMY_FIRST'))


class BaseStrategyMgr(object):

    def __init__(self):
        pass

    def update(self, dc, am):
        pass

    def reset(self):
        pass


class ZergStrategyMgr(BaseStrategyMgr):

    def __init__(self):
        super(ZergStrategyMgr, self).__init__()
        self._army = Army()
        self._strategy = Strategy.RUSH

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._army.update(dc.dd.combat_pool)

        self._organize_army()
        self._command_army(dc.dd.enemy_pool,
                           dc.dd.combat_command_queue)

    def reset(self):
        self._army = Army()

    def _organize_army(self):
        self._create_fixed_size_squads(squad_size=5)

    def _create_fixed_size_squads(self, squad_size):
        while len(self._army.unsquaded_units) >= squad_size:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, squad_size))

    def _command_army(self, enemy, cmd_queue):
        if self._strategy == Strategy.RUSH:
            self._command_army_rush(enemy, cmd_queue)
        else:
            self._command_army_economy_first(self, enemy, cmd_queue)

    def _command_army_rush(self, enemy_pool, cmd_queue):
        if len(self._army.squads) >= 1 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)

    def _command_army_economy_first(self, enemy_pool, cmd_queue):
        if len(self._army.squads) >= 5 and len(enemy_pool.enemy_clusters) >= 1:
            for squad in self._army.squads:
                cmd = CombatCommand(
                    type=CombatCmdType.ATTACK,
                    squad=squad,
                    position=enemy_pool.weakest_cluster.centroid)
                cmd_queue.push(cmd)
