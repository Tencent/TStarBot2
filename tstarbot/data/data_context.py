"""data context"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.data.queue.build_command_queue import BuildCommandQueue
from tstarbot.data.queue.combat_command_queue import CombatCommandQueue
from tstarbot.data.queue.scout_command_queue import ScoutCommandQueue

from tstarbot.data.pool.base_pool import BasePool
from tstarbot.data.pool.building_pool import BuildingPool
from tstarbot.data.pool.worker_pool import WorkerPool
from tstarbot.data.pool.combat_pool import CombatPool
from tstarbot.data.pool.enemy_pool import EnemyPool


class StaticData(object):
    def __init__(self):
        self._obs = None

    def update(self, timestep):
        self._obs = timestep.observation

    @property
    def obs(self):
        return self._obs

class DynamicData(object):
    def __init__(self):
        self.build_command_queue = BuildCommandQueue()
        self.combat_command_queue = CombatCommandQueue()
        self.scout_command_queue = ScoutCommandQueue()

        self.building_pool = BuildingPool()
        self.worker_pool = WorkerPool()
        self.combat_pool = CombatPool()
        self.enemy_pool = EnemyPool()
        self.base_pool = BasePool(self)

    def update(self, timestep):
        # update command queues

        # update pools
        self.building_pool.update(timestep)
        self.worker_pool.update(timestep)
        self.combat_pool.update(timestep)
        self.enemy_pool.update(timestep)
        #self.base_pool.update(timestep)

        # update statistic

    def reset(self):
        self.base_pool.reset()

class DataContext:
    def __init__(self):
        self._dynamic = DynamicData()
        self._static = StaticData()

    def update(self, timestep):
        # self._obs = timestep.observation
        self._dynamic.update(timestep)
        self._static.update(timestep)

    def reset(self):
        print('***DataContext reset***')
        self._dynamic.reset()

    @property
    def dd(self):
        return self._dynamic

    @property
    def sd(self):
        return self._static
