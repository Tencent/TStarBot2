"""CombatPool Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from enum import Enum

from tstarbot.data.pool import macro_def as tm
from tstarbot.data.pool.pool_base import PoolBase


CombatUnitStatus = Enum('CombatUnitStatus', ('IDLE', 'COMBAT', 'SCOUT'))


class CombatUnit(object):

  def __init__(self, unit):
    self._unit = unit
    self._status = CombatUnitStatus.IDLE
    self._lost = False

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

  def set_lost(self, lost):
    self._lost = lost

  def is_lost(self):
    return self._lost

  def set_status(self, status):
    self._status = status

  def update(self, u):
    if u.int_attr.tag == self._unit.int_attr.tag:  # is the same unit
      self._unit = u


class CombatUnitPool(PoolBase):
  def __init__(self):
    super(PoolBase, self).__init__()
    self._units = dict()

  def update(self, timestep):
    units = timestep.observation['units']

    # set all combat unit 'lost' state
    for k, b in self._units.items():
      b.set_lost(True)

    # update unit
    for u in units:
      if self._is_combat_unit(u):
        self._add_unit(u)

    # delete lost unit
    del_keys = []
    for k, b in self._units.items():
      if b.is_lost():
        del_keys.append(k)

    for k in del_keys:
      del self._units[k]

  def get_by_tag(self, tag):
    return self._units.get(tag, None)

  def employ_combat_unit(self, employ_status, unit_type):
    idles = [u for u in self.units
             if
             u.unit.int_attr.unit_type == unit_type and u.status == CombatUnitStatus.IDLE]

    if len(idles) > 0:
      u = idles[0]
      self._units[u.unit.int_attr.tag].set_status(employ_status)
      return u.unit
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

  def _add_unit(self, u):
    tag = u.int_attr.tag

    if tag in self._units:
      self._units[u.tag].update(u)
    else:
      self._units[u.tag] = CombatUnit(u)

    self._units[u.tag].set_lost(False)
