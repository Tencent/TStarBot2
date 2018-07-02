from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID
from collections import deque


def unit_count(units, tech_tree, alliance=1):
  count = {}
  for unit_id in UNIT_TYPEID:  # init
    count[unit_id.value] = 0

  for u in units:  # add unit
    if u.int_attr.alliance == alliance:
      if u.unit_type in count:
        count[u.unit_type] += 1
      else:
        count[u.unit_type] = 1

  eggs = []
  for u in units:  # get all the eggs
    if u.unit_type == UNIT_TYPEID.ZERG_EGG.value:
      eggs.append(u)

  for unit_type, data in tech_tree.m_unitTypeData.items():  # add unit in egg
    if data.isUnit:
      count[unit_type] += sum(
          [(len(egg.orders) > 0 and
            egg.orders[0].ability_id == data.buildAbility)
           for egg in eggs])
  return count


def unique_unit_count(units, tech_tree, alliance=1):
  count = unit_count(units, tech_tree, alliance)
  unit_alias = {UNIT_TYPEID.ZERG_BANELING.value:
                    [UNIT_TYPEID.ZERG_BANELINGBURROWED.value,
                     UNIT_TYPEID.ZERG_BANELINGCOCOON.value],
                UNIT_TYPEID.ZERG_BROODLORD.value:
                    [UNIT_TYPEID.ZERG_BROODLORDCOCOON.value],
                UNIT_TYPEID.ZERG_DRONE.value:
                    [UNIT_TYPEID.ZERG_DRONEBURROWED.value],
                UNIT_TYPEID.ZERG_HYDRALISK.value:
                    [UNIT_TYPEID.ZERG_HYDRALISKBURROWED.value],
                UNIT_TYPEID.ZERG_INFESTOR.value:
                    [UNIT_TYPEID.ZERG_INFESTORBURROWED.value],
                UNIT_TYPEID.ZERG_LURKERMP.value:
                    [UNIT_TYPEID.ZERG_LURKERMPBURROWED.value,
                     UNIT_TYPEID.ZERG_LURKERMPEGG.value],
                UNIT_TYPEID.ZERG_OVERSEER.value:
                    [UNIT_TYPEID.ZERG_OVERLORDCOCOON.value],
                UNIT_TYPEID.ZERG_QUEEN.value:
                    [UNIT_TYPEID.ZERG_QUEENBURROWED.value],
                UNIT_TYPEID.ZERG_RAVAGER.value:
                    [UNIT_TYPEID.ZERG_RAVAGERCOCOON.value],
                UNIT_TYPEID.ZERG_ROACH.value:
                    [UNIT_TYPEID.ZERG_ROACHBURROWED.value],
                UNIT_TYPEID.ZERG_SPORECRAWLER.value:
                    [UNIT_TYPEID.ZERG_SPORECRAWLERUPROOTED.value],
                UNIT_TYPEID.ZERG_SWARMHOSTMP.value:
                    [UNIT_TYPEID.ZERG_SWARMHOSTBURROWEDMP.value],
                UNIT_TYPEID.ZERG_ZERGLING.value:
                    [UNIT_TYPEID.ZERG_ZERGLINGBURROWED.value]}
  for unit_type, alias in unit_alias.items():
    for a in alias:
      count[unit_type] += count[a]
  return count


class BuildOrderQueue(object):
  def __init__(self, tech_tree):
    self.queue = deque()
    self.TT = tech_tree

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
