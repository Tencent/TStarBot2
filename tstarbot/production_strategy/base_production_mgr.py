from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from pysc2.lib.typeenums import RACE
from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID
from tstarbot.production_strategy.util import BuildOrderQueue
from tstarbot.production_strategy.build_cmd import *


class BaseProductionMgr(object):
  def __init__(self, dc, race=RACE.Zerg, use_search=True):
    self.onStart = True
    self.race = race
    self.use_search = use_search
    self.TT = dc.sd.TT
    self.build_order = BuildOrderQueue(self.TT)
    self.obs = None
    self.cut_in_item = []
    self.born_pos = None
    self.verbose = 0
    self.strategy = 'RUSH'
    self._init_config(dc)

  def _init_config(self, dc):
    if hasattr(dc, 'config'):
      if hasattr(dc.config, 'production_verbose'):
        self.verbose = dc.config.production_verbose
      if hasattr(dc.config, 'production_strategy'):
        self.strategy = dc.config.production_strategy

  def reset(self):
    self.onStart = True
    self.build_order.clear_all()
    self.obs = None
    self.cut_in_item = []
    self.born_pos = None

  def update(self, data_context, act_mgr):
    self.obs = data_context.sd.obs

    # Get goal and search build order
    if self.onStart:
      self.build_order.set_build_order(self.get_opening_build_order())
      bases = data_context.dd.base_pool.bases
      self.born_pos = [[bases[tag].unit.float_attr.pos_x,
                        bases[tag].unit.float_attr.pos_y]
                       for tag in bases][0]
      self.onStart = False
    elif self.build_order.is_empty():
      goal = self.get_goal(data_context)
      if self.use_search:
        self.build_order.set_build_order(self.perform_search(goal))
      else:
        self.build_order.set_build_order(goal)

    # determine whether to Expand
    current_item = self.build_order.current_item()
    if (self.base_unit() not in self.cut_in_item
        and self.should_expand_now(data_context)
        and (current_item is None
             or current_item.unit_id != self.base_unit())):
      self.build_order.queue_as_highest(self.base_unit())
      self.cut_in_item.append(self.base_unit())
      if self.verbose > 0:
        print('Cut in: {}'.format(self.base_unit()))

    # determine whether to build extractor
    if (self.gas_unit() not in self.cut_in_item and
        self.need_more_extractor(data_context)):
      self.build_order.queue_as_highest(self.gas_unit())
      self.cut_in_item.append(self.gas_unit())
      if self.verbose > 0:
        print('Cut in: {}'.format(self.gas_unit()))

    self.add_upgrade(data_context)

    self.post_update(data_context)

    # deal with the dead lock if exists (supply, uprade, tech ...)
    if not self.build_order.is_empty():
      while self.detect_dead_lock(data_context):
        pass

    self.check_supply()

    # check resource, builder, requirement and determine the build base
    current_item = self.build_order.current_item()
    if current_item and self.can_build(current_item, data_context):
      if current_item.isUnit:
        if self.set_build_base(current_item, data_context):
          self.build_order.remove_current_item()
          if current_item.unit_id in self.cut_in_item:
            self.cut_in_item.remove(current_item.unit_id)
          if self.verbose > 0:
            print('Produce: {}'.format(current_item.unit_id))
      else:  # Upgrade
        if self.upgrade(current_item, data_context):
          self.build_order.remove_current_item()
          if current_item.unit_id in self.cut_in_item:
            self.cut_in_item.remove(current_item.unit_id)
          if self.verbose > 0:
            print('Upgrade: {}'.format(current_item.unit_id))

    if self.should_gas_first(data_context):
      data_context.dd.build_command_queue.put(
          BuildCmdHarvest(gas_first=True))

    if self.should_mineral_first(data_context):
      data_context.dd.build_command_queue.put(
          BuildCmdHarvest(gas_first=False))

  def supply_unit(self):
    if self.race == RACE.Zerg:
      return UNIT_TYPEID.ZERG_OVERLORD
    if self.race == RACE.Protoss:
      return UNIT_TYPEID.PROTOSS_PYLON
    if self.race == RACE.Terran:
      return UNIT_TYPEID.TERRAN_SUPPLYDEPOT
    raise Exception("Race type Error. typeenums.RACE.")

  def gas_unit(self):
    if self.race == RACE.Zerg:
      return UNIT_TYPEID.ZERG_EXTRACTOR
    if self.race == RACE.Protoss:
      return UNIT_TYPEID.PROTOSS_ASSIMILATOR
    if self.race == RACE.Terran:
      return UNIT_TYPEID.TERRAN_REFINERY
    raise Exception("Race type Error. typeenums.RACE.")

  def base_unit(self):
      if self.race == RACE.Zerg:
          return UNIT_TYPEID.ZERG_HATCHERY
      if self.race == RACE.Protoss:
          return UNIT_TYPEID.PROTOSS_NEXUS
      if self.race == RACE.Terran:
          return UNIT_TYPEID.TERRAN_COMMANDCENTER
      raise Exception("Race type Error. typeenums.RACE.")

  def detect_dead_lock(self, data_context):
    current_item = self.build_order.current_item()
    builder = None
    for unit_type in current_item.whatBuilds:
      if (self.has_unit(unit_type)
          or self.unit_in_progress(unit_type)
          or unit_type == UNIT_TYPEID.ZERG_LARVA.value):
        builder = unit_type
        break
    if builder is None and len(current_item.whatBuilds) > 0:
      builder_id = [unit_id for unit_id in UNIT_TYPEID
                    if unit_id.value == current_item.whatBuilds[0]]
      self.build_order.queue_as_highest(builder_id[0])
      if self.verbose > 0:
        print('Cut in: {}'.format(builder_id[0]))
      return True
    required_unit = None
    for unit_type in current_item.requiredUnits:
      if self.has_unit(unit_type) or self.unit_in_progress(unit_type):
        required_unit = unit_type
        break
    if required_unit is None and len(current_item.requiredUnits) > 0:
      required_id = [unit_id for unit_id in UNIT_TYPEID
                     if unit_id.value == current_item.requiredUnits[0]]
      self.build_order.queue_as_highest(required_id[0])
      if self.verbose > 0:
        print('Cut in: {}'.format(required_id[0]))
      return True
    required_upgrade = None
    for upgrade_type in current_item.requiredUpgrades:
      if (not self.has_upgrade(data_context, [upgrade_type])
          and not self.upgrade_in_progress(upgrade_type)):
        required_upgrade = upgrade_type
        break
    if required_upgrade is not None:
      required_id = [up_id for up_id in UPGRADE_ID
                     if up_id.value == required_upgrade]
      self.build_order.queue_as_highest(required_id[0])
      if self.verbose > 0:
        print('Cut in: {}'.format(required_id[0]))
    return False

  def food_used(self):
    return self.obs["player"][3]

  def food_cap(self):
    return self.obs["player"][4]

  def find_unit_by_tag(self, tag):
    return [unit for unit in self.obs['units'] if unit.tag == tag]

  def check_supply(self):
    current_item = self.build_order.current_item()
    # No enough supply and supply not in building process
    if (current_item is not None
        and self.food_used() + current_item.supplyCost
            > self.food_cap() - min(20.0, max(0.0, (self.food_cap()-30)/5))
        and current_item.supplyCost > 0
        and not self.supply_in_progress()
        and current_item.unit_id != self.supply_unit()
        and self.food_cap() < 200):
      self.build_order.queue_as_highest(self.supply_unit())
      if self.verbose > 0:
        print('Cut in: {}'.format(self.supply_unit()))

  def has_unit(self, unit_type, alliance=1):
    return any([(unit.unit_type == unit_type and unit.int_attr.alliance == alliance)
                for unit in self.obs["units"]])

  def find_unit(self, unit_type, alliance=1):
    return [unit for unit in self.obs["units"]
            if unit.unit_type == unit_type
            and unit.int_attr.alliance == alliance]

  def has_building_built(self, unit_type_list, alliance=1):
    if len(unit_type_list) == 0:
      return True
    for unit in self.obs["units"]:
      if (unit.unit_type in unit_type_list
          and unit.int_attr.alliance == alliance
          and unit.float_attr.build_progress == 1):
        return True
    return False

  def has_upgrade(self, dc, upgrade_type_list):
    return (all([up_type in dc.sd.obs['raw_data'].player.upgrade_ids
                 for up_type in upgrade_type_list])
            or len(upgrade_type_list) == 0)

  def upgrade_in_progress(self, upgrade_type, alliance=1):
    data = self.TT.getUpgradeData(upgrade_type)
    builders = [unit for unit in self.obs['units']
                if unit.unit_type in data.whatBuilds
                and unit.int_attr.alliance == alliance]
    in_progress = [builder for builder in builders
                   if len(builder.orders) > 0
                   and builder.orders[0].ability_id == data.buildAbility]
    return in_progress

  def unit_in_progress(self, unit_type, alliance=1):
    data = self.TT.getUnitData(unit_type)
    order_unit = data.whatBuilds
    if UNIT_TYPEID.ZERG_LARVA.value in order_unit:
      order_unit = [UNIT_TYPEID.ZERG_EGG.value]
    for unit in self.obs['units']:
      if (unit.unit_type == unit_type
          and unit.int_attr.alliance == alliance
          and unit.float_attr.build_progress < 1):
        return True
      if (unit.unit_type in order_unit
          and unit.int_attr.alliance == alliance
          and len(unit.orders) > 0
          and unit.orders[0].ability_id == data.buildAbility):
        return True
    return False

  def should_expand_now(self, data_context):
    return False

  def need_more_extractor(self, data_context):
    return False

  def get_opening_build_order(self):
    return []

  def perform_search(self, goal):  # TODO: implement search algorithm here
    return goal

  def get_goal(self, dc):
    return []

  def add_upgrade(self, dc):
    pass

  def post_update(self, dc):
    pass

  def set_build_base(self, build_item, data_context):
    return False

  def upgrade(self, build_item, data_context):
    return False

  def can_build(self, build_item, data_context):  # check resource requirement
    return False

  def supply_in_progress(self):
    return self.unit_in_progress(self.supply_unit().value)

  def should_gas_first(self, dc):
    return True

  def should_mineral_first(self, dc):
    return False
