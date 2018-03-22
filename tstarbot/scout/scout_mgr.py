"""Scout Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseScoutMgr(object):
    def __init__(self):
        pass

    def update(self, dc, am):
        pass


class ZergScoutMgr(BaseScoutMgr):
    def __init__(self):
        super(ZergScoutMgr, self).__init__()

    def update(self, dc, am):
        super(ZergScoutMgr, self).update(dc, am)

        actions = []

        # TODO: impl here

        am.push_actions(actions)
