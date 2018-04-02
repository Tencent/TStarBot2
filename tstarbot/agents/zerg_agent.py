"""Scripted Zerg agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
from copy import deepcopy
import platform

from pysc2.agents import base_agent
from tstarbot.strategy.strategy_mgr import ZergStrategyMgr
from tstarbot.production.production_mgr import ZergProductionMgr
from tstarbot.building.building_mgr import ZergBuildingMgr
from tstarbot.resource.resource_mgr import ZergResourceMgr
from tstarbot.combat.combat_mgr import ZergCombatMgr
from tstarbot.scout.scout_mgr import ZergScoutMgr
from tstarbot.data.data_context import DataContext
from tstarbot.act.act_mgr import ActMgr
from tstarbot.agents.mac_agent_patch import *


class ZergAgent(base_agent.BaseAgent):
    """A ZvZ Zerg agent for full game map."""

    def __init__(self):
        super(ZergAgent, self).__init__()

        self.dc = DataContext()
        self.am = ActMgr()

        self.strategy_mgr = ZergStrategyMgr()
        self.production_mgr = ZergProductionMgr()
        self.building_mgr = ZergBuildingMgr()
        self.resource_mgr = ZergResourceMgr()
        self.combat_mgr = ZergCombatMgr()
        self.scout_mgr = ZergScoutMgr()

        self.episode_step = 0
        self.is_larva_selected = 0
        self.is_base_selected = 0
        self.is_base_grouped = 0
        self.is_mac_os = 'Linux' not in platform.platform()

    def step(self, timestep):
        super(ZergAgent, self).step(timestep)

        if self.is_mac_os:
            if self.episode_step == 0:
                self.dc.update(timestep=timestep)
                actions = self.am.pop_actions()
            else:
                if not check_larva_selected(timestep.observation) and self.is_base_selected == 0:
                    self.is_larva_selected = 0

                if self.is_larva_selected == 0:
                    if self.is_base_selected == 0 or self.is_base_grouped == 0:
                        if self.is_base_grouped == 0:
                            if self.is_base_selected == 0:
                                action = micro_select_hatchery(timestep.observation)
                                self.is_base_selected = 1
                            else:
                                action = micro_group_selected(timestep.observation, 1)
                                self.is_base_grouped = 1
                        else:
                            action = micro_recall_selected_group(timestep.observation, 1)
                            self.is_base_selected = 1
                    else:
                        action = micro_select_larvas(timestep.observation)
                        self.is_base_selected = 0
                        self.is_larva_selected = 1
                    if action is None or action[0] not in timestep.observation["available_actions"]:
                        actions = []
                    else:
                        actions = pysc2_actions.FunctionCall(*action)
                else:
                    actions = self.process(timestep)
        else:
            actions = self.process(timestep)

        self.episode_step += 1
        return actions

    def process(self, timestep):
        self.dc.update(timestep)  # update data context

        # Brain
        self.strategy_mgr.update(self.dc, self.am)
        self.production_mgr.update(self.dc, self.am)

        # Construct
        self.building_mgr.update(self.dc, self.am)
        self.resource_mgr.update(self.dc, self.am)

        # Battle
        self.combat_mgr.update(self.dc, self.am)
        self.scout_mgr.update(self.dc, self.am)

        return self.am.pop_actions()

    def reset(self):
        super(ZergAgent, self).reset()
        # module reset
        self.dc.reset()
        self.strategy_mgr.reset()
        self.production_mgr.reset()
        self.building_mgr.reset()
        self.resource_mgr.reset()
        self.combat_mgr.reset()
        self.scout_mgr.reset()

        # scalar reset
        self.episode_step = 0
        self.is_larva_selected = 0
        self.is_base_selected = 0
        self.is_base_grouped = 0
