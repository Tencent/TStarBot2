from enum import Enum, unique

@unique
class DataType(Enum):
    COMMAND = 0
    POOL = 1
    STATISTIC = 2
    STATIC = 3

class CommandBase(object):
    def __init__(self, uid):
        self._uid = uid

    def cmd_type(self):
        raise NotImplementedError

class CommandQueueBase(object):
    def put(self, idx, cmd):
        pass

    def get(self, idx, cmd):
        pass

    def clear_all(self):
        pass

class PoolBase(object):
    def update(self, obs):
        raise NotImplementedError



class StatisticBase(object):
    def data_type(self):
        return DataType.STATISTIC

    def set(self, val):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError

