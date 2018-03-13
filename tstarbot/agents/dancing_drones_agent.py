"""Adopted from

Zheng Yang's demo_bot.py showing the per-unit-control via raw interface of s2client-proto.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.obs_mgr import DancingDronesObsMgr
from tstarbot.resource_mgr import DancingDronesResourceMgr
from tstarbot.act_mgr import ActMgr
from pysc2.agents import base_agent


class DancingDronesAgent(base_agent.BaseAgent):
    """An agent that makes drones dancing.

    Show how to send per-unit-control actions."""

    def __init__(self):
        super(DancingDronesAgent, self).__init__()
        self.obs_mgr = DancingDronesObsMgr()
        self.resource_mgr = DancingDronesResourceMgr()
        self.act_mgr = ActMgr()

    def step(self, timestep):
        super(DancingDronesAgent, self).step(timestep)
        self.obs_mgr.update(timestep=timestep)
        self.resource_mgr.update(self.obs_mgr, self.act_mgr)
        return self.act_mgr.pop_actions()
