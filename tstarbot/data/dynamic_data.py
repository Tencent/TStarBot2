import collections

from tstarbot.data.build_command_queue import BuildCommandQueue
from tstarbot.data.combat_command_queue import CombatCommandQueue
from tstarbot.data.scout_command_queue import ScoutCommandQueue

from tstarbot.data.base_pool import BasePool
from tstarbot.data.building_pool import BuildingPool
from tstarbot.data.worker_pool import WorkerPool
from tstarbot.data.combat_pool import CombatPool
from tstarbot.data.enemy_pool import EnemyPool

class DynamicData(object):
    def __init__(self):
        self.build_command_queue = BuildCommandQueue()
        self.combat_command_queue = CombatCommandQueue()
        self.scout_command_queue = ScoutCommandQueue()

        self.base_pool = BasePool()
        self.building_pool = BuildingPool()
        self.worker_pool = WorkerPool()
        self.combat_pool = CombatPool()
        self.enemy_pool = EnemyPool()

    def update(self, obs):
        # update command queues

        # update pools
        self.base_pool.update(obs)
        self.building_pool.update(obs)
        self.worker_pool.update(obs)
        self.combat_pool.update(obs)
        self.enemy_pool.update(obs)

        # update statistic


    def des(self):
        return 'Dynamic Data set'
