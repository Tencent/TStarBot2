"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import math
from s2clientprotocol import sc2api_pb2 as sc_pb
import pysc2.lib.typeenums as tp


class BaseCombatMgr:
    def __init__(self):
        pass

    def update(self, dc, am):
        pass


class ZergCombatMgr(BaseCombatMgr):
    """ A zvz Zerg combat manager """

    def __init__(self):
        super(ZergCombatMgr, self).__init__()

    def update(self, dc, am):
        super(ZergCombatMgr, self).update(dc, am)

        actions = list()

        # TODO: impl

        am.push_actions(actions)
