"""Building Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

class BaseBuildingMgr:
    def __init__(self):
        pass

    def update(self):
        pass

class ZergBuildingMgr(BaseBuildingMgr):
    def __init__(self):
        super(ZergBuildingMgr, self).__init__()

    def update(self, am):
        super(ZergBuildingMgr, self).update()

        actions = []
        # TODO: impl here
        #print('a', obs_mgr.a)
        #print('b', obs_mgr.b)

        am.push_actions(actions)