"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseProductionMgr:
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass


class ZergProductionMgr(BaseProductionMgr):
    def __init__(self):
        super(ZergProductionMgr, self).__init__()

    def update(self, obs_mgr, act_mgr):
        super(ZergProductionMgr, self).__init__()

        actions = []
        # TODO: impl here

        act_mgr.push_actions(actions)
