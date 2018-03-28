from tstarbot.data.queue.command_queue_base import CommandQueueBase
from enum import Enum, unique

@unique
class ScoutCommandType(Enum):
    MOVE = 0


class ScoutCommandQueue(CommandQueueBase):
    def __init__(self):
        SCOUT_CMD_ID_BASE = 300000000
        super(ScoutCommandQueue, self).__init__(SCOUT_CMD_ID_BASE)
