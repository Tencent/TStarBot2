"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseStrategyMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass

    def reset(self):
        pass


class ZergStrategyMgr(BaseStrategyMgr):
    def __init__(self):
        super(ZergStrategyMgr, self).__init__()

    def update(self, dc, am):
        super(ZergStrategyMgr, self).update(dc, am)

        actions = []

        # TODO: impl here

        am.push_actions(actions)
