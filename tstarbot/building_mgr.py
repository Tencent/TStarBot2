"""Building Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseBuildingMgr(object):
    def __init__(self):
        pass

    def update(self, dc, act_mgr):
        pass


class ZergBuildingMgr(BaseBuildingMgr):
    def __init__(self):
        super(ZergBuildingMgr, self).__init__()

    def update(self, dc, am):
        super(ZergBuildingMgr, self).update(dc, am)

        actions = []

        # TODO: impl here

        am.push_actions(actions)
