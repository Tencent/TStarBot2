"""Scripted Zerg agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
from copy import deepcopy

from pysc2.agents import base_agent
from tstarbot.strategy_mgr import ZergStrategyMgr
from tstarbot.building_mgr import ZergBuildingMgr
from tstarbot.combat_mgr import ZergCombatMgr
from tstarbot.scout_mgr import ZergScoutMgr
from tstarbot.data.data_context import DataContext
from tstarbot.act_mgr import ActMgr

class ZergAgent(base_agent.BaseAgent):
    """A ZvZ Zerg agent for full game map."""

    def __init__(self):
        super(ZergAgent, self).__init__()

        self.dc = DataContext()
        self.act_mgr = ActMgr()

        self.strategy_mgr = ZergStrategyMgr()
        self.building_mgr = ZergBuildingMgr()
        self.combat_mgr = ZergCombatMgr()
        self.scout_mgr = ZergScoutMgr()

    def step(self, timestep):
        super(ZergAgent, self).step(timestep)

        # update data context
        self.dc.update(timestep)

        self.strategy_mgr.update(self.dc, self.act_mgr)
        self.building_mgr.update(self.dc, self.act_mgr)
        self.combat_mgr.update(self.dc, self.act_mgr)
        self.scout_mgr.update(self.dc, self.act_mgr)

        return self.act_mgr.pop_actions()
