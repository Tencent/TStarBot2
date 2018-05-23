"""Combat Command Queue."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from enum import Enum

from tstarbot.strategy.squad import Squad


CombatCmdType = Enum('CombatCmdType', ('MOVE', 'ATTACK', 'DEFEND', 'RALLY', 'ROCK'))


class CombatCommand(object):

    def __init__(self, type, squad, position):
        assert isinstance(type, CombatCmdType)
        assert isinstance(squad, Squad)
        assert isinstance(position, dict)
        assert 'x' in position and 'y' in position

        self._type = type
        self._squad = squad
        self._position = position

    def __repr__(self):
        return ('CombatCmd(Type(%s), Squad(%s), Position(%s))' %
                (self._type, self._squad, self._position))

    @property
    def type(self):
        return self._type

    @property
    def squad(self):
        return self._squad

    @property
    def position(self):
        return self._position


# TODO: update CommandQueueBase if hope to inherit it.
class CombatCommandQueue(object):

    def __init__(self):
        self._queue = collections.deque()

    def push(self, cmd):
        assert isinstance(cmd, CombatCommand)
        self._queue.append(cmd)

    def pull(self):
        return [] if len(self._queue) == 0 else self._queue.pop()

    def clear(self):
        self._queue.clear()
