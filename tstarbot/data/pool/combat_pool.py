"""CombatPool Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from enum import Enum

from tstarbot.data.pool import macro_def as tm
from tstarbot.data.pool.pool_base import PoolBase


# TODO(@xinghai): delete CombatUnit if not necessary.

class CombatUnit(object):

    def __init__(self, unit):
        self._unit = unit

    @property
    def unit(self):
        return self._unit

    @property
    def tag(self):
        return self._unit.tag

    @property
    def type(self):
        return self._unit.unit_type

    @property
    def position(self):
        return {'x': self._unit.float_attr.pos_x,
                'y': self._unit.float_attr.pos_y}


class CombatPool(PoolBase):

    def __init__(self):
        super(PoolBase, self).__init__()
        self._units = dict()

    def update(self, timestep):
        units = timestep.observation['units']
        for u in units:
            if self._is_combat_unit(u):
                self._units[u.tag] = CombatUnit(u)

    def get_by_tag(self, tag):
        return self._units.get(tag, None)

    @property
    def num_units(self):
        return len(self._units)

    @property
    def units(self):
        return self._units.values()

    def _is_combat_unit(self, u):
        if (u.unit_type in tm.COMBAT_UNITS and
            u.int_attr.alliance == tm.AllianceType.SELF.value):
            return True
        else:
            return False
