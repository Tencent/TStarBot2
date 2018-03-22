"""Adopted from

lxhan
A rule based multi-agent micro-management bot. seems working well that sometimes can reach grandmaster human player's performance.
Run bin/eval_micro.py to see the game.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.combat import DefeatRoachesCombatMgr
from pysc2.agents import base_agent
from pysc2.lib import stopwatch
from tstarbot.data.demo_pool import DefeatRoaches
from tstarbot.act_mgr import ActMgr

sw = stopwatch.sw

class MicroDefeatRoachesAgent(base_agent.BaseAgent):
    """An agent for the DefeatRoaches map."""

    def __init__(self):
        super(MicroDefeatRoachesAgent, self).__init__()
        self.pool = DefeatRoaches()
        self.am = ActMgr()
        self._mgr = DefeatRoachesCombatMgr()

    def step(self, timestep):
        super(MicroDefeatRoachesAgent, self).step(timestep)
        return self.mystep(timestep)

    @sw.decorate
    def mystep(self, timestep):
        self.pool.update(timestep.observation)
        self._mgr.update(self.pool, self.am)

        actions = self.am.pop_actions()
        return actions
