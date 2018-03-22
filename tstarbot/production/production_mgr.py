"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseProductionMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self):
        super(ZergProductionMgr, self).__init__()

    def update(self, dc, am):
        super(ZergProductionMgr, self).update(dc, am)

        actions = []
        # TODO: impl here

        am.push_actions(actions)
