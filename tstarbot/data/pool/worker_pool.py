from tstarbot.data.pool.pool_base import PoolBase

class WorkerPool(PoolBase):
    def __init__(self):
        super(PoolBase, self).__init__()

    def update(self, timestep):
        pass

    def find_nearest_by_tag(self, unit_tag):
        pass

    def find_nearest_by_pos(self, x, y):
        pass