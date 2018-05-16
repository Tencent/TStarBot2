"""CombatPool Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.data.pool import macro_def as tm
from tstarbot.data.pool.pool_base import PoolBase
from enum import Enum

CombatUnitStatus = Enum('CombatUnitStatus', ('IDLE', 'COMBAT', 'SCOUT'))


class CombatUnit(object):

    def __init__(self, unit):
        self._unit = unit
        self._status = CombatUnitStatus.IDLE

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
    def status(self):
        return self._status

    @property
    def position(self):
        return {'x': self._unit.float_attr.pos_x,
                'y': self._unit.float_attr.pos_y}


class CombatUnitPool(PoolBase):
    def __init__(self):
        super(PoolBase, self).__init__()
        self._units = dict()

    def update(self, timestep):
        units = timestep.observation['units']
        self._units.clear()
        for u in units:
            if self._is_combat_unit(u):
                self._units[u.tag] = CombatUnit(u)

    def get_by_tag(self, tag):
        return self._units.get(tag, None)

    def employ_combat_unit(self, employ_status, unit_type):
        idles = [u for u in self.units
                 if u.unit.int_attr.unit_type == unit_type and u.status == CombatUnitStatus.IDLE]
        if len(idles) > 0:
            idles[0].status = employ_status
            return idles[0].unit
        return None

    @property
    def num_units(self):
        return len(self._units)

    @property
    def units(self):
        return self._units.values()

    @staticmethod
    def _is_combat_unit(u):
        if (u.unit_type in tm.COMBAT_UNITS and
                    u.int_attr.alliance == tm.AllianceType.SELF.value):
            return True
        else:
            return False
