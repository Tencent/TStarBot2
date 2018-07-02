""" Scripted Zerg agent."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import importlib
from time import sleep

from pysc2.agents import base_agent

from tstarbot.combat_strategy.combat_strategy_mgr import ZergStrategyMgr
from tstarbot.production_strategy.production_mgr import ZergProductionMgr
from tstarbot.building.building_mgr import ZergBuildingMgr
from tstarbot.resource.resource_mgr import ZergResourceMgr
from tstarbot.combat.combat_mgr import ZergCombatMgr
from tstarbot.scout.scout_mgr import ZergScoutMgr
from tstarbot.data.data_context import DataContext
from tstarbot.act.act_mgr import ActMgr


class ZergAgent(base_agent.BaseAgent):
  """A ZvZ Zerg agent for full game map."""

  def __init__(self, **kwargs):
    super(ZergAgent, self).__init__()
    self._sleep_per_step = None

    config = None
    if kwargs.get('config_path'):  # use the config file
      config = importlib.import_module(kwargs['config_path'])
    self._init_config(config)

    self.dc = DataContext(config)
    self.am = ActMgr()

    self.strategy_mgr = ZergStrategyMgr(self.dc)
    self.production_mgr = ZergProductionMgr(self.dc)
    self.building_mgr = ZergBuildingMgr(self.dc)
    self.resource_mgr = ZergResourceMgr(self.dc)
    self.combat_mgr = ZergCombatMgr(self.dc)
    self.scout_mgr = ZergScoutMgr(self.dc)

  def _init_config(self, cfg):
    if hasattr(cfg, 'sleep_per_step'):
      self._sleep_per_step = cfg.sleep_per_step

  def step(self, timestep):
    super(ZergAgent, self).step(timestep)

    if self._sleep_per_step:
      sleep(self._sleep_per_step)

    self.dc.update(timestep)  # update data context

    # Brain
    self.strategy_mgr.update(self.dc, self.am)
    self.production_mgr.update(self.dc, self.am)

    # Battle
    self.combat_mgr.update(self.dc, self.am)
    self.scout_mgr.update(self.dc, self.am)

    # Construct
    self.building_mgr.update(self.dc, self.am)
    self.resource_mgr.update(self.dc, self.am)

    return self.am.pop_actions()

  def reset(self):
    super(ZergAgent, self).reset()
    self.dc.reset()
    self.strategy_mgr.reset()
    self.production_mgr.reset()
    self.building_mgr.reset()
    self.resource_mgr.reset()
    self.combat_mgr.reset()
    self.scout_mgr.reset()
