"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random

from tstarbot.strategy.squad import Squad
from tstarbot.strategy.army import Army
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.queue.combat_command_queue import CombatCommand


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

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)
        self._army.update(dc.dd.combat_pool)

        self._organize_army()
        self._command_army(dc.dd.enemy_pool,
                           dc.dd.combat_command_queue)

    def reset(self):
        self._army = Army()

    def _organize_army(self):
        if len(self._army.unsquaded_units) >= 5:
            self._army.create_squad(
                random.sample(self._army.unsquaded_units, 5))

    def _command_army(self, enemy, cmd_queue):
        if len(self._army.squads) > 0:
            for squad in self._army.squads:
                cmd = CombatCommand(type=CombatCmdType.ATTACK,
                                    squad=squad,
                                    position=(0, 0))
                cmd_queue.push(cmd)
                # print(cmd)
