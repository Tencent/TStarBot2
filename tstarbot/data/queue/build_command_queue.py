from tstarbot.data.queue.command_queue_base import CommandQueueBase
<<<<<<< 0c0994916471ddda77afa1ed7becf3dfa8abe7e3
from enum import Enum, unique

@unique
class BuildCommandType(Enum):
    BUILD = 0
    CANCEL = 1

class BuildCommandQueue(CommandQueueBase):
    def __init__(self):
        BUILD_CMD_ID_BASE = 100000000
        super(BuildCommandQueue, self).__init__(BUILD_CMD_ID_BASE)

if __name__ == "__main__":
    q = BuildCommandQueue()
    q.put(0, BuildCommandType.BUILD, {'unit_id': 100, 'count': 1})
    q.put(1, BuildCommandType.BUILD, {'unit_id': 200, 'count': 2})
    #q.clear_all()

    cmds = q.get(1)
    for cmd in cmds:
        print(cmd)
