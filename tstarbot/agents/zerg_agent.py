"""Scripted Zerg agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
from copy import deepcopy

from pysc2.agents import base_agent
from tstarbot.strategy_mgr import ZergStrategyMgr
from tstarbot.production_mgr import ZergProductionMgr
from tstarbot.building_mgr import ZergBuildingMgr
from tstarbot.resource_mgr import ZergResourceMgr
from tstarbot.combat_mgr import ZergCombatMgr
from tstarbot.scout_mgr import ZergScoutMgr
from tstarbot.obs_mgr import ZergObsMgr
from tstarbot.act_mgr import ActMgr


class ZergAgent(base_agent.BaseAgent):
    """A ZvZ Zerg agent for full game map."""

    def __init__(self):
        super(ZergAgent, self).__init__()

        self.obs_mgr = ZergObsMgr()

        self.strategy_mgr = ZergStrategyMgr()
        self.production_mgr = ZergProductionMgr()
        self.building_mgr = ZergBuildingMgr()
        self.resource_mgr = ZergResourceMgr()
        self.combat_mgr = ZergCombatMgr()
        self.scout_mgr = ZergScoutMgr()

        self.act_mgr = ActMgr()

    def step(self, timestep):
        super(ZergAgent, self).step(timestep)

        self.obs_mgr.update(timestep=timestep)

        self.strategy_mgr.update(self.obs_mgr, self.act_mgr)
        self.production_mgr.update(self.obs_mgr, self.act_mgr)
        self.building_mgr.update(self.obs_mgr, self.act_mgr)
        self.resource_mgr.update(self.obs_mgr, self.act_mgr)
        self.combat_mgr.update(self.obs_mgr, self.act_mgr)
        self.scout_mgr.update(self.obs_mgr, self.act_mgr)

        return self.act_mgr.pop_actions()
