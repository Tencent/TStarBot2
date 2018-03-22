from tstarbot.data.pool.pool_base import PoolBase

class BasePool(PoolBase):
    def __init__(self):
        super(PoolBase, self).__init__()

    def update(self, timestep):
        pass

