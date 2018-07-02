from collections import deque
from tstarbot.data.queue.command_queue_base import CommandQueueBase
from enum import Enum, unique


@unique
class BuildCommandType(Enum):
  BUILD = 0
  EXPAND = 1
  CANCEL = 2


class BuildCommandQueue(CommandQueueBase):
  def __init__(self):
    BUILD_CMD_ID_BASE = 100000000
    super(BuildCommandQueue, self).__init__(BUILD_CMD_ID_BASE)


class BuildCommandQueueV2(object):
  """ A left-in-right-out queue (first in first out) """

  def __init__(self):
    self._q = deque()

  def put(self, item):
    """ push an item at left """
    self._q.appendleft(item)

  def get(self):
    """ pop an item from right """
    return self._q.pop()

  def empty(self):
    return False if self._q else True

  def size(self):
    return len(self._q)


if __name__ == "__main__":
  # usage of BuildCommandQueue
  q = BuildCommandQueue()
  q.put(0, BuildCommandType.BUILD, {'unit_id': 100, 'count': 1})
  q.put(1, BuildCommandType.BUILD, {'unit_id': 200, 'count': 2})
  # q.clear_all()

  cmds = q.get(1)
  for cmd in cmds:
    print(cmd)

  # usage of BuildCommandQueueV2
  from collections import namedtuple

  BuildCmdBuilding = namedtuple('build_cmd_building', ['base_tag'])
  BuildCmdUnit = namedtuple('build_cmd_unit', ['base_tag'])

  qq = BuildCommandQueueV2()
  qq.put(BuildCmdBuilding(base_tag=34567))
  qq.put(BuildCmdUnit(base_tag=8879))
  c1 = qq.get()
  print(c1)
  qq.put(BuildCmdUnit(base_tag=445891))
  c2 = qq.get()
  print(c2)
  c3 = qq.get()
  print(c3)
