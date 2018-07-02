"""
A rule based multi-agent micro-management bot for the mini-game DefeatRoaches.
Adopted from the code originally writen by lxhan(slivermoda).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.agents import base_agent
from pysc2.lib import stopwatch

from tstarbot.combat import DefeatRoachesCombatMgr
from tstarbot.data.demo_dc import DefeatRoaches
from tstarbot.act.act_mgr import ActMgr

sw = stopwatch.sw


class MicroDefeatRoachesAgent(base_agent.BaseAgent):
  """An agent for the DefeatRoaches map."""

  def __init__(self):
    super(MicroDefeatRoachesAgent, self).__init__()
    self.dc = DefeatRoaches()
    self.am = ActMgr()
    self._mgr = DefeatRoachesCombatMgr()

  def step(self, timestep):
    super(MicroDefeatRoachesAgent, self).step(timestep)
    return self.mystep(timestep)

  @sw.decorate
  def mystep(self, timestep):
    self.dc.update(timestep)
    self._mgr.update(self.dc, self.am)

    actions = self.am.pop_actions()
    return actions
