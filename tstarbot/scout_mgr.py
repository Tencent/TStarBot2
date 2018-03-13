"""Scout Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseScoutMgr:
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass


class ZergScoutMgr(BaseScoutMgr):
    def __init__(self):
        super(ZergScoutMgr, self).__init__()
        self.marines = None
        self.roaches = None

    def update(self, obs_mgr, act_mgr):
        super(ZergScoutMgr, self).__init__()

        actions = list()
        # TODO: impl here

        act_mgr.push_actions(actions)
