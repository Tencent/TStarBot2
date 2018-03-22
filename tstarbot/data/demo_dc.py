from tstarbot.data.pool.pool_base import PoolBase
import pysc2.lib.typeenums as tp


class DancingDrones(PoolBase):
    """ Let drones dance around their base.
    adopted from Zheng Yang's code."""

    def __init__(self):
        super(DancingDrones, self).__init__()
        self._drone_ids = []
        self._hatcherys = []

    def update(self, timestamp):
        units = timestamp.observation['units']
        self._locate_hatcherys(units)
        self._update_drone(units)

    def _locate_hatcherys(self, units):
        tmp_hatcherys = []
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.ZERG_HATCHERY.value:
                tmp_hatcherys.append((u.float_attr.pos_x, u.float_attr.pos_y, u.float_attr.pos_z))
        self._hatcherys = tmp_hatcherys

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

    def key(self):
        return 'dancing_drones'


class DefeatRoaches(PoolBase):
    """ for DefeatRoaches Minimap.
    Adopted from lxhan's code
    """

    def __init__(self):
        self.marines = []  # fro self
        self.roaches = []  # for enemy

    def update(self, timestep):
        units = timestep.observation['units']
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

    def key(self):
        return 'defeat_roaches'
