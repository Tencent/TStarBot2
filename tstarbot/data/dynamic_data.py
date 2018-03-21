import collections
from tstarbot.data import ids, DataType

DYNAMIC_DATA_KEYS = ids(type=DataType.POOL)

class DynamicData(collections.namedtuple('DynamicData', DYNAMIC_DATA_KEYS)):
    __slots__ = ()

    def des(self):
        return 'Dynamic Data set'

