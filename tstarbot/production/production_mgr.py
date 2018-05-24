"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.production.prod_advarms import ZergProdAdvArms
from tstarbot.production.prod_rush import ZergProdRush
from tstarbot.production.prod_defandadv import ZergProdDefAndAdv


class ZergProductionMgr(object):
    def __init__(self, dc):
        self.strategy = 'DEF_AND_ADV'
        if hasattr(dc, 'config'):
            if hasattr(dc.config, 'production_strategy'):
                self.strategy = dc.config.production_strategy
        if self.strategy == 'RUSH':
            self.c = ZergProdRush(dc)
        elif self.strategy == 'ADV_ARMS':
            self.c = ZergProdAdvArms(dc)
        elif self.strategy == 'DEF_AND_ADV':
            self.c = ZergProdDefAndAdv(dc)
        else:
            raise Exception('Unknow production strategy: "%s"' % str(self.strategy))

    def reset(self):
        return self.c.reset()

    def update(self, dc, am):
        return self.c.update(dc, am)
