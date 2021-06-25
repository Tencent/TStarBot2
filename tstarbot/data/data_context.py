"""data context"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.data_raw import get_data_raw
from pysc2.lib import TechTree

from tstarbot.data.queue.build_command_queue import BuildCommandQueue
from tstarbot.data.queue.build_command_queue import BuildCommandQueueV2
from tstarbot.data.queue.combat_command_queue import CombatCommandQueue
from tstarbot.data.queue.scout_command_queue import ScoutCommandQueue
from tstarbot.data.pool.base_pool import BasePool
from tstarbot.data.pool.building_pool import BuildingPool
from tstarbot.data.pool.worker_pool import WorkerPool
from tstarbot.data.pool.combat_pool import CombatUnitPool
from tstarbot.data.pool.enemy_pool import EnemyPool
from tstarbot.data.pool.scout_pool import ScoutPool
from tstarbot.data.pool.opponent_pool import OppoPool

class StaticData(object):
  def __init__(self, config):
    self._obs = None
    self._timestep = None
    self.game_version = '3.16.1'
    self._data_raw = get_data_raw(self.game_version)

    if hasattr(config, 'game_version'):
      self.game_version = config.game_version
    self.TT = TechTree()
    self.TT.update_version(self.game_version)

  def update(self, timestep):
    self._obs = timestep.observation
    self._timestep = timestep

  @property
  def obs(self):
    return self._obs

  @property
  def timestep(self):
    return self._timestep

  @property
  def data_raw(self):
    return self._data_raw


class DynamicData(object):
  def __init__(self, config):
    self.build_command_queue = BuildCommandQueueV2()
    self.combat_command_queue = CombatCommandQueue()
    self.scout_command_queue = ScoutCommandQueue()

    self.building_pool = BuildingPool()
    self.worker_pool = WorkerPool()
    self.combat_pool = CombatUnitPool()
    self.base_pool = BasePool(self)
    self.enemy_pool = EnemyPool(self)
    self.scout_pool = ScoutPool(self)
    self.oppo_pool = OppoPool()

  def update(self, timestep):
    # update command queues

    # update pools
    self.building_pool.update(timestep)
    self.worker_pool.update(timestep)
    self.combat_pool.update(timestep)
    self.base_pool.update(timestep)
    self.enemy_pool.update(timestep)
    self.scout_pool.update(timestep)

    # update statistic

  def reset(self):
    self.base_pool.reset()
    self.scout_pool.reset()
    self.oppo_pool.reset()
    self.enemy_pool.reset()


class DataContext:
  def __init__(self, config):
    self.config = config
    self._dynamic = DynamicData(config)
    self._static = StaticData(config)

  def update(self, timestep):
    # self._obs = timestep.observation
    self._dynamic.update(timestep)
    self._static.update(timestep)

  def reset(self):
    # print('***DataContext reset***')
    self._dynamic.reset()

  @property
  def dd(self):
    return self._dynamic

  @property
  def sd(self):
    return self._static
