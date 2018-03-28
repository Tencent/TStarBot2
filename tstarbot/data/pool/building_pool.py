from tstarbot.data.pool.pool_base import PoolBase
from pysc2.lib.typeenums import UNIT_TYPEID

class Building(object):
    def __init__(self, unit):
        self._unit = unit
        self._lost = False    # is building lost

    def unit(self):
        return self._unit

    def set_lost(self, lost):
        self._lost = lost

    def is_lost(self):
        return self._lost

    def __str__(self):
        u = self._unit
        return "tag {}, type {}, alliance {}".format(u.int_attr.tag, u.int_attr.unit_type, u.int_attr.alliance)

class BuildingPool(PoolBase):
    def __init__(self):
        super(PoolBase, self).__init__()

        self.building_types = set([
            # Zerg
            UNIT_TYPEID.ZERG_HATCHERY.value,
            UNIT_TYPEID.ZERG_SPINECRAWLER.value,
            UNIT_TYPEID.ZERG_SPORECRAWLER.value,
            UNIT_TYPEID.ZERG_EXTRACTOR.value,
            UNIT_TYPEID.ZERG_SPAWNINGPOOL.value,
            UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value,
            UNIT_TYPEID.ZERG_ROACHWARREN.value,
            UNIT_TYPEID.ZERG_BANELINGNEST.value,
            UNIT_TYPEID.ZERG_CREEPTUMOR.value,
            UNIT_TYPEID.ZERG_LAIR.value,
            UNIT_TYPEID.ZERG_HYDRALISKDEN.value,
            UNIT_TYPEID.ZERG_LURKERDENMP.value,
            UNIT_TYPEID.ZERG_SPIRE.value,
            UNIT_TYPEID.ZERG_NYDUSNETWORK.value,
            UNIT_TYPEID.ZERG_INFESTATIONPIT.value,
            UNIT_TYPEID.ZERG_HIVE.value,
            UNIT_TYPEID.ZERG_GREATERSPIRE.value,
            UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value,

            # Terran

            # Protoss

        ])
        self._buildings = {}    # unit_tag -> Building

    def update(self, timestep):
        units = timestep.observation['units']
        self._update_building(units)

    def exist_any(self, unit_type):
        for k, b in self._buildings.items():
            if b.unit().int_attr.unit_type == unit_type:
                return True

        return False

    def list_buildings(self, unit_type):
        buildings = []
        for k, b in self._buildings.items():
            if b.unit().int_attr.unit_type == unit_type:
                buildings.append(b.unit())

        return buildings

    def _update_building(self, units):
        # set all building 'lost' state
        for k, b in self._buildings.items():
            b.set_lost(True)

        # update / insert building
        for u in units:
            # print("type {}, owner {}, alliance {}".format(u.int_attr.unit_type, u.int_attr.owner, u.int_attr.alliance))

            if u.int_attr.unit_type in self.building_types and u.int_attr.alliance == 1:
                # print("building found: tag {}, type {}".format(u.int_attr.tag, u.int_attr.unit_type))
                tag = u.int_attr.tag
                self._buildings[tag] = Building(u)

        # delete lost buildings
        del_keys = []
        for k, b in self._buildings.items():
            if b.is_lost():
                u = b.unit()
                # print("found lost: tag {}, type {}".format(u.int_attr.tag, u.int_attr.unit_type))
                del_keys.append(k)

        for k in del_keys:
            del self._buildings[k]
