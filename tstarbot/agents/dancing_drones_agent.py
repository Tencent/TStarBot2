"""Adopted from

Demonstrate the per-unit-control via raw interface of s2client-proto.
Adopted from demo_bot.py written by zhengyang.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.agents import base_agent

from tstarbot.building.dancing_drones_mgr import DancingDronesMgr
from tstarbot.data.demo_dc import DancingDrones
from tstarbot.act.act_mgr import ActMgr


class DancingDronesAgent(base_agent.BaseAgent):
  """An agent that makes drones dancing.

  Show how to send per-unit-control actions."""

  def __init__(self):
    super(DancingDronesAgent, self).__init__()
    # self.dc = DataContext()
    self.dc = DancingDrones()
    self.am = ActMgr()

    self._mgr = DancingDronesMgr(self.dc)

  def step(self, timestep):
    super(DancingDronesAgent, self).step(timestep)
    # print(timestep)
    self.dc.update(timestep)
    self._mgr.update(self.dc, self.am)
    return self.am.pop_actions()
