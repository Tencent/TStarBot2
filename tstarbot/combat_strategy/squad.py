"""Squad Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from enum import Enum
from pysc2.lib.typeenums import UNIT_TYPEID
from tstarbot.data.pool import macro_def as tm
from tstarbot.data.pool.combat_pool import CombatUnitStatus


SquadStatus = Enum('SquadStatus', ('IDLE', 'MOVE', 'ATTACK', 'DEFEND', 'SCOUT', 'ROCK'))
MutaliskSquadStatus = Enum('SquadStatus', ('IDLE', 'PHASE1', 'PHASE2'))


class Squad(object):

    def __init__(self, units, uniform=None):
        self._units = units  # combat_unit
        self._status = SquadStatus.IDLE
        self.combat_status = MutaliskSquadStatus.IDLE
        self._uniform = uniform
        for u in units:
            assert u.unit.int_attr.alliance == tm.AllianceType.SELF.value

    def __repr__(self):
        return ('Squad(Units(%d), Roaches(%d), Zerglings(%d))' %
                (self.num_units, self.num_roach_units, self.num_zergling_units))

    def update(self, combat_unit_pool):
        tags = [u.tag for u in self._units]
        self._units = list()
        for tag in tags:
            combat_unit = combat_unit_pool.get_by_tag(tag)
            if combat_unit is not None and combat_unit.status != CombatUnitStatus.SCOUT:
                self._units.append(combat_unit)

    @property
    def num_units(self):
        return len(self._units)

    @property
    def num_hydralisk_units(self):
        return len(self.hydralisk_units)

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
    def hydralisk_units(self):
        return [u for u in self._units
                if u.type == UNIT_TYPEID.ZERG_HYDRALISK.value]

    @property
    def roach_units(self):
        return [u for u in self._units
                if u.type == UNIT_TYPEID.ZERG_ROACH.value]
    @property
    def zergling_units(self):
        return [u for u in self._units
                if u.type == UNIT_TYPEID.ZERG_ZERGLING.value]

    @property
    def uniform(self):
        return self._uniform

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def centroid(self):
        x, y = 0, 0
        if len(self._units) > 0:
            x = sum(u.position['x'] for u in self._units) / len(self._units)
            y = sum(u.position['y'] for u in self._units) / len(self._units)
        return {'x': x, 'y': y}
