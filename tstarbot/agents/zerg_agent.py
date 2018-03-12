"""Scripted Zerg agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
from copy import deepcopy

from pysc2.agents import base_agent



class ZergAgent(base_agent.BaseAgent):
    """A zerg agent for full game map."""

    def __init__(self):
        super(ZergAgent, self).__init__()
        self.obs_mgr = ObsMgr()

        self.act_mgr = ActMgr()

    def step(self, timestep):
        super(ZergAgent, self).step(timestep)

        self.obs_mgr.update(timestep=timestep)
