from tstarbot.data.queue.command_queue_base import CommandQueueBase
from enum import Enum, unique

@unique
class CombatCommandType(Enum):
    MOVE = 0
    ATTACK = 1
    DEFEND = 2
    RETREAT = 3


class CombatCommandQueue(CommandQueueBase):
    def __init__(self):
        COMBAT_CMD_ID_BASE = 200000000
        super(CombatCommandQueue, self).__init__(COMBAT_CMD_ID_BASE)
