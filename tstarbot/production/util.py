from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID
from collections import deque
import numpy as np


def dist_to_pos(unit, pos):
    return ((unit.float_attr.pos_x - pos[0])**2 +
            (unit.float_attr.pos_y - pos[1])**2)**0.5


def find_nearest(units, unit):
    """ find the nearest one to 'unit' within the list 'units' """
    if not units:
        return None
    x, y = unit.float_attr.pos_x, unit.float_attr.pos_y
    dd = np.asarray([dist_to_pos(u, [x, y]) for u in units])
    return units[dd.argmin()]


def find_nearest_to_pos(units, pos):
    """ find the nearest one to pos within the list 'units' """
    if not units:
        return None
    dd = np.asarray([dist_to_pos(u, pos) for u in units])
    return units[dd.argmin()]


class BuildOrderQueue(object):
    def __init__(self, TT):
        self.queue = deque()
        self.TT = TT

    def set_build_order(self, unit_list):
        for unit_id in unit_list:
            if type(unit_id) == UNIT_TYPEID:
                build_item = self.TT.getUnitData(unit_id.value)
            elif type(unit_id) == UPGRADE_ID:
                build_item = self.TT.getUpgradeData(unit_id.value)
            else:
                raise Exception('Unknown unit_id {}'.format(unit_id))
            build_item.unit_id = unit_id
            self.queue.append(build_item)

    def size(self):
        return len(self.queue)

    def is_empty(self):
        return len(self.queue) == 0

    def current_item(self):
        if len(self.queue) > 0:
            return self.queue[0]
        else:
            return None

    def remove_current_item(self):
        if len(self.queue) > 0:
            self.queue.popleft()

    def queue_as_highest(self, unit_id):
        if type(unit_id) == UNIT_TYPEID:
            build_item = self.TT.getUnitData(unit_id.value)
        elif type(unit_id) == UPGRADE_ID:
            build_item = self.TT.getUpgradeData(unit_id.value)
        else:
            raise Exception('Unknown unit_id {}'.format(unit_id))
        build_item.unit_id = unit_id
        self.queue.appendleft(build_item)

    def queue(self, unit_id):
        if type(unit_id) == UNIT_TYPEID:
            build_item = self.TT.getUnitData(unit_id.value)
        elif type(unit_id) == UPGRADE_ID:
            build_item = self.TT.getUpgradeData(unit_id.value)
        else:
            raise Exception('Unknown unit_id {}'.format(unit_id))
        build_item.unit_id = unit_id
        self.queue.append(build_item)

    def clear_all(self):
        self.queue.clear()

    def reset(self):
        self.queue.clear()