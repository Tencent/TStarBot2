"""Squad Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from enum import Enum
from pysc2.lib.typeenums import UNIT_TYPEID


SquadStatus = Enum('SquadStatus', ('IDLE','MOVE', 'ATTACK', 'DEFEND'))


class Squad(object):

    def __init__(self, units):
        self._units = units
        self._status = SquadStatus.IDLE

    def __repr__(self):
        return ('Squad(Units(%d), Roaches(%d), Zerglings(%d))' %
                (self.num_units, self.num_roach_units, self.num_zergling_units))

    def update(self, combat_pool):
        tags = [u.tag for u in self._units]
        self._units.clear()
        for tag in tags:
            unit = combat_pool.get_by_tag(tag)
            if unit is not None:
                self._units.append(unit)

    @property
    def num_units(self):
        return len(self._units)

    @property
    def num_roach_units(self):
        return len(self.roach_units)

    @property
    def num_zergling_units(self):
        return len(self.zergling_units)

    @property
    def units(self):
        return self._units

    @property
    def roach_units(self):
        return [u for u in self._units
                if u.type == UNIT_TYPEID.ZERG_ROACH.value]
    @property
    def zergling_units(self):
        return [u for u in self._units
                if u.type == UNIT_TYPEID.ZERG_ZERGLING.value]

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def centroid(self):
        x = sum(u.float_attr.pos_x for u in self._units) / len(self._units)
        y = sum(u.float_attr.pos_x for u in self._units) / len(self._units)
        return {'pos_x':x, 'pos_y':y}
