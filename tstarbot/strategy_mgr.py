"""Strategy Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class BaseStrategyMgr:
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass


class ZergStrategyMgr(BaseStrategyMgr):
    def __init__(self):
        super(ZergStrategyMgr, self).__init__()

    def update(self, obs_mgr, act_mgr):
        super(ZergStrategyMgr, self).update(obs_mgr, act_mgr)

        actions = []
        # TODO: impl here
        obs_mgr.a = 3
        obs_mgr.b = 4

        act_mgr.push_actions(actions)
