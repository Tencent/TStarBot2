"""Adopted from

lxhan
A rule based multi-agent micro-management bot. seems working well that sometimes can reach grandmaster human player's performance.
Run bin/eval_micro.py to see the game.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.combat import DefeatRoachesCombatMgr
from tstarbot.data.demo_dc import DefeatRoaches
from tstarbot.act.act_mgr import ActMgr
from pysc2.agents import base_agent
from pysc2.lib import stopwatch

sw = stopwatch.sw


class MicroDefeatRoachesAgent(base_agent.BaseAgent):
    """An agent for the DefeatRoaches map."""

    def __init__(self):
        super(MicroDefeatRoachesAgent, self).__init__()
        self.dc = DefeatRoaches()
        self.am = ActMgr()
        self._mgr = DefeatRoachesCombatMgr(self.dc)

    def step(self, timestep):
        super(MicroDefeatRoachesAgent, self).step(timestep)
        return self.mystep(timestep)

    @sw.decorate
    def mystep(self, timestep):
        self.dc.update(timestep)
        self._mgr.update(self.dc, self.am)

        actions = self.am.pop_actions()
        return actions
