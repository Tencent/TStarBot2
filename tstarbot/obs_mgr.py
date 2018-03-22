"""Observation Manager"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pysc2.lib.typeenums as tp


class BaseObsMgr(object):
    def __init__(self):
        self.obs_feat = None
        self.obs_raw = None
        self.a_pool = None
        self.b_pool = None

    def update(self, timestep):
        self.obs_feat = timestep.observation
        # self.obs_raw = timestep.observation_raw
        self.units = timestep.observation['units']


class DancingDronesObsMgr(BaseObsMgr):
    """ Let drones dance around their base.

    adopted from Zheng Yang's code."""

    def __init__(self):
        super(DancingDronesObsMgr, self).__init__()
        self._drone_ids = []
        self._hatcherys = []

    def update(self, timestep):
        super(DancingDronesObsMgr, self).update(timestep=timestep)

        units = timestep.observation['units']
        self._locate_hatcherys(units)
        self._update_drone(units)

    def _locate_hatcherys(self, units):
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.ZERG_HATCHERY.value:
                self._hatcherys.append((u.float_attr.pos_x, u.float_attr.pos_y, u.float_attr.pos_z))

    def _update_drone(self, units):
        drone_ids = []
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.ZERG_DRONE.value:
                drone_ids.append(u.tag)

        self._drone_ids = drone_ids

    def get_drones(self):
        return self._drone_ids

    def get_hatcherys(self):
        return self._hatcherys


class DefeatRoachesObsMgr(BaseObsMgr):
    """ for DefeatRoaches Minimap.

    Adopted from lxhan's code
    """

    def __init__(self):
        super(DefeatRoachesObsMgr, self).__init__()
        self.marines = []  # fro self
        self.roaches = []  # for enemy

    def update(self, timestep):
        super(DefeatRoachesObsMgr, self).update(timestep=timestep)

        units = timestep.observation['units']
        # print(units)
        self.collect_marine(units)
        self.collect_roach(units)

    def collect_marine(self, units):
        marines = []
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.TERRAN_MARINE.value and u.int_attr.owner == 1:
                marines.append(u)
                # print("marine assigned_harvesters: {}".format(u.int_attr.assigned_harvesters))
        self.marines = marines

    def collect_roach(self, units):
        roaches = []
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.ZERG_ROACH.value and u.int_attr.owner == 2:
                roaches.append(u)
                # print("roach target: {}".format(u.int_attr.engaged_target_tag))
        self.roaches = roaches

    def get_marines(self):
        return self.marines

    def get_roaches(self):
        return self.roaches


class ZergObsMgr(BaseObsMgr):
    """ Z v Z obs manager
    """

    def __init__(self):
        super(ZergObsMgr, self).__init__()
        self.units = None
        self.a = None
        self.b = None

    def update(self, dc, am):
        super(ZergObsMgr, self).update(timestep=timestep)

        self.units = timestep.observation['units']
