"""Adopted from

lxhan
A rule based multi-agent micro-management bot. seems working well that sometimes can reach grandmaster human player's performance.
Run bin/eval_micro.py to see the game.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.obs_mgr import DefeatRoachesObsMgr
from tstarbot.combat_mgr import DefeatRoachesCombatMgr
from tstarbot.act_mgr import ActMgr
from pysc2.agents import base_agent


class MicroDefeatRoachesAgent(base_agent.BaseAgent):
    """An agent for the DefeatRoaches map."""

    def __init__(self):
        super(MicroDefeatRoachesAgent, self).__init__()
        self.obs_mgr = DefeatRoachesObsMgr()
        self.combat_mgr = DefeatRoachesCombatMgr()
        self.act_mgr = ActMgr()

    def step(self, timestep):
        super(MicroDefeatRoachesAgent, self).step(timestep)
        self.obs_mgr.update(timestep=timestep)
        self.combat_mgr.update(self.obs_mgr, self.act_mgr)
        return self.act_mgr.pop_actions()
