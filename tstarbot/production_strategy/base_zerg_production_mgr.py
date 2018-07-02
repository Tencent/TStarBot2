"""Production Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import operator
import distutils.version

from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import UPGRADE_ID

from tstarbot.data.pool.macro_def import BASE_UNITS
from tstarbot.util.geom import dist_to_pos
from tstarbot.util.unit import find_nearest_to_pos
from tstarbot.util.unit import find_nearest
from tstarbot.production_strategy.base_production_mgr import BaseProductionMgr
from tstarbot.production_strategy.build_cmd import *



class ZergBaseProductionMgr(BaseProductionMgr):
  def __init__(self, dc):
    super(ZergBaseProductionMgr, self).__init__(dc)

  def reset(self):
    super(ZergBaseProductionMgr, self).reset()

  def update(self, data_context, act_mgr):
    super(ZergBaseProductionMgr, self).update(data_context, act_mgr)
    self.spawn_larva(data_context)

    actions = []
    act_mgr.push_actions(actions)

  def should_expand_now(self, dc):
    if self.expand_waiting_resource(dc):
      return False
    expand_worker = {0: 0, 1: 20, 2: 33, 3: 40, 4: 45, 5: 50, 6: 55,
                     7: 60, 8: 64, 9: 65, 10: 65, 11: 65, 12: 200}
    num = len([unit for unit in self.obs['units']
               if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_DRONE.value
               and unit.int_attr.alliance == 1])
    bases = dc.dd.base_pool.bases
    ideal_harvesters_all = 0
    base_num = 0
    for base_tag in bases:
      base_num += 1
      if bases[base_tag].unit.float_attr.build_progress == 1:
        ideal_harvesters_all += self.ideal_harvesters(bases[base_tag])
    base_num = min(12, base_num)
    if (num > min(ideal_harvesters_all, expand_worker[base_num])
        and not self.unit_in_progress(self.base_unit().value)):
      return True
    return False

  def need_more_extractor(self, dc):
    gas_worker_num = {1: 19, 2: 25, 3: 30, 4: 35, 5: 40}
    bases = dc.dd.base_pool.bases
    n_w = len([unit for unit in self.obs['units']
               if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_DRONE.value
               and unit.int_attr.alliance == 1])
    n_g = len([u for u in self.obs['units']
               if u.unit_type == UNIT_TYPEID.ZERG_EXTRACTOR.value
               and u.int_attr.vespene_contents > 100
               and u.int_attr.alliance == 1])  # 100 gas ~ 30s ?
    if self.unit_in_progress(UNIT_TYPEID.ZERG_EXTRACTOR.value):
      return False

    gas_num = 0
    for base_tag in bases:
      if (bases[base_tag].unit.float_attr.build_progress < 1
          or len(bases[base_tag].worker_set) == 0):
        continue
      gas_num += 2 - len(bases[base_tag].vb_set)
    if gas_num == 0:
      return False

    if n_g == 0:
      current_item = self.build_order.current_item()
      if current_item.gasCost > 0:
        return True
    if 0 < n_g < 6 and n_w >= gas_worker_num[n_g]:
      return True
    play_info = self.obs["player"]
    minerals, vespene = play_info[1:3]
    if n_g >= 6 and (minerals > 1000 and vespene < 200):
      return True
    return False

  def post_update(self, dc):
    if (UNIT_TYPEID.ZERG_QUEEN not in self.cut_in_item
        and self.need_more_queen(dc)):
      # print('need more queens!')
      self.build_order.queue_as_highest(UNIT_TYPEID.ZERG_QUEEN)
      self.cut_in_item.append(UNIT_TYPEID.ZERG_QUEEN)
      if self.verbose > 0:
        print('Cut in: {}'.format(UNIT_TYPEID.ZERG_QUEEN))

  def need_more_queen(self, dc):
    if self.unit_in_progress(UNIT_TYPEID.ZERG_QUEEN.value):
      return False
    n_q = len([unit for unit in self.obs['units']
               if unit.int_attr.unit_type == UNIT_TYPEID.ZERG_QUEEN.value
               and unit.int_attr.alliance == 1])
    bases = dc.dd.base_pool.bases
    n_base = len([tag for tag in bases
                  if bases[tag].unit.float_attr.build_progress == 1])
    n_army = len([u for u in self.obs['units']
                  if (u.unit_type == UNIT_TYPEID.ZERG_ROACH.value
                      or u.unit_type == UNIT_TYPEID.ZERG_HYDRALISK.value)
                  and u.int_attr.alliance == 1])
    if n_army > 12 and n_q < min(n_base, 3):
      return True
    return False

  def spawn_larva(self, dc):
    queens = self.find_unit(UNIT_TYPEID.ZERG_QUEEN.value)
    for queen in queens:
      if queen.float_attr.energy > 75 and len(queen.orders) == 0:
        bases = dc.dd.base_pool.bases
        base = find_nearest([bases[tag].unit for tag in bases], queen)
        if base is not None:
          dc.dd.build_command_queue.put(
              BuildCmdSpawnLarva(queen_tag=queen.tag,
                                 base_tag=base.tag))

  def building_in_progress(self, unit_id, alliance=1):
    unit_data = self.TT.getUnitData(unit_id.value)
    if not unit_data.isBuilding:
      print('building_in_progress can only be used for buildings!')
    for unit in self.obs['units']:
      if (unit.unit_type == unit_id.value
          and unit.int_attr.alliance == alliance
          and unit.float_attr.build_progress < 1):
        return True
      if (unit.unit_type == UNIT_TYPEID.ZERG_DRONE.value
          and unit.int_attr.alliance == alliance
          and len(unit.orders) > 0
          and unit.orders[0].ability_id == unit_data.buildAbility):
        return True
    return False

  def queen_in_progress(self, dc):
    data = self.TT.getUnitData(UNIT_TYPEID.ZERG_QUEEN.value)
    bases = dc.dd.base_pool.bases
    for tag in bases:
      if any([order.ability_id == data.buildAbility
              for order in bases[tag].unit.orders]):
        return True
    return False

  @staticmethod
  def expand_waiting_resource(dc):
    l = dc.dd.build_command_queue.size()
    for _ in range(l):
      cmd = dc.dd.build_command_queue.get()
      dc.dd.build_command_queue.put(cmd)
      if type(cmd) == BuildCmdExpand:
        return True
    return False

  def can_build(self, build_item, dc):  # check resource requirement
    if not (self.has_building_built(build_item.whatBuilds)
            and self.has_building_built(build_item.requiredUnits)
            and self.has_upgrade(dc, build_item.requiredUpgrades)
            and not self.expand_waiting_resource(dc)):
      return False
    play_info = self.obs["player"]
    if (build_item.supplyCost > 0
        and play_info[3] + build_item.supplyCost > play_info[4]):
      return False
    if build_item.unit_id == UNIT_TYPEID.ZERG_HATCHERY:
      return self.obs['player'][1] >= build_item.mineralCost - 100
    return (self.obs['player'][1] >= build_item.mineralCost
            and self.obs['player'][2] >= build_item.gasCost)

  def set_build_base(self, build_item, data_context):
    bases = data_context.dd.base_pool.bases
    builders = build_item.whatBuilds
    if build_item.isBuilding:  # build building
      if UNIT_TYPEID.ZERG_DRONE.value not in builders:  # morph building
        build_units = [u for u in self.obs['units']
                       if u.unit_type in builders]
        build_unit = find_nearest_to_pos(build_units, self.born_pos)
        data_context.dd.build_command_queue.put(
          BuildCmdMorph(unit_tag=build_unit.tag,
                        ability_id=build_item.buildAbility))
        return True
      if build_item.unit_id == UNIT_TYPEID.ZERG_EXTRACTOR:
        tag = self.find_base_to_build_extractor(bases)
      elif build_item.unit_id == UNIT_TYPEID.ZERG_SPINECRAWLER:
        tag = self.find_base_to_build_spinecrawler(bases)
      else:
        tag = self.find_base_to_build(bases)
      if tag is not None:
        if build_item.unit_id == UNIT_TYPEID.ZERG_HATCHERY:
          pos = self.find_base_pos(data_context)
          if pos is not None:
            data_context.dd.build_command_queue.put(
                BuildCmdExpand(base_tag=tag, pos=pos, builder_tag=None))
        else:
          data_context.dd.build_command_queue.put(
              BuildCmdBuilding(base_tag=tag, unit_type=build_item.unit_id.value))
        return True
    else:  # build unit
      if (UNIT_TYPEID.ZERG_LARVA.value not in builders
          and UNIT_TYPEID.ZERG_HATCHERY.value not in builders):
        build_units = [u for u in self.obs['units']
                       if u.unit_type in builders]
        build_unit = find_nearest_to_pos(build_units, self.born_pos)
        data_context.dd.build_command_queue.put(
            BuildCmdMorph(unit_tag=build_unit.tag,
                          ability_id=build_item.buildAbility))
        return True
      if build_item.unit_id == UNIT_TYPEID.ZERG_DRONE:
        tag = self.find_base_to_produce_drone(bases)
      elif build_item.unit_id == UNIT_TYPEID.ZERG_QUEEN:
        tag = self.find_base_to_produce_queue(bases)
      else:
        tag = self.find_base_to_produce_unit(bases)
      if tag is not None:
        data_context.dd.build_command_queue.put(
            BuildCmdUnit(base_tag=tag,
                         unit_type=build_item.unit_id.value))
        return True
    return False

  def find_base_to_build_extractor(self, bases):
    max_num = 0  # find base with most workers and need extractor
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      worker_num = self.assigned_harvesters(bases[base_tag])
      if worker_num > max_num and len(bases[base_tag].vb_set) < 2:
        tag = base_tag
        max_num = worker_num
    return tag

  def find_base_with_most_workers(self, bases):
    max_num = 0  # find base with most workers
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      worker_num = self.assigned_harvesters(bases[base_tag])
      if worker_num > max_num:
        tag = base_tag
        max_num = worker_num
    return tag

  def find_base_to_build(self, bases):
    d_min = 1000  # find base closed to born position
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      worker_num = self.assigned_harvesters(bases[base_tag])
      d = dist_to_pos(bases[base_tag].unit, self.born_pos)
      if worker_num > 0 and d < d_min:
        tag = base_tag
        d_min = d
    return tag

  def find_base_to_build_spinecrawler(self, bases):
    d_max = -1  # find base furthest to born position
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      worker_num = self.assigned_harvesters(bases[base_tag])
      d = dist_to_pos(bases[base_tag].unit, self.born_pos)
      if worker_num > 0 and d > d_max:
        tag = base_tag
        d_max = d
    return tag

  def find_base_to_produce_drone(self, bases):
    max_gap = -200  # find base need worker most
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      num_gap = (self.ideal_harvesters(bases[base_tag])
                 - self.assigned_harvesters(bases[base_tag]))
      if num_gap > max_gap and len(bases[base_tag].larva_set) > 0:
        tag = base_tag
        max_gap = num_gap
    return tag

  def find_base_to_produce_queue(self, bases):
    max_gap = -200  # find base not in morph and need worker most
    max_queen = 20
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      orders = bases[base_tag].unit.orders
      num_gap = (self.ideal_harvesters(bases[base_tag])
                 - self.assigned_harvesters(bases[base_tag]))
      queen_num = len(bases[base_tag].queen_set)
      if (len(orders) == 0
          and (queen_num < max_queen
               or (queen_num == max_queen and num_gap > max_gap))):
        tag = base_tag
        max_gap = num_gap
        max_queen = queen_num
    return tag

  @staticmethod
  def find_base_to_produce_unit(bases):
    larva_count = 0  # find base with most larvas
    tag = None
    for base_tag in bases:
      if bases[base_tag].unit.float_attr.build_progress < 1:
        continue
      num_larva = len(bases[base_tag].larva_set)
      if num_larva > larva_count:
        tag = base_tag
        larva_count = num_larva
    return tag

  @staticmethod
  def find_base_pos_old(dc):
    areas = dc.dd.base_pool.resource_cluster
    bases = dc.dd.base_pool.bases
    d_min = 10000
    pos = None
    for area in areas:
      if area not in [base.resource_area for base in bases.values()]:
        d = dc.dd.base_pool.home_dist[area]
        if 5 < d < d_min:
          pos = area.ideal_base_pos
          d_min = d
    return pos

  def find_base_pos(self, dc):
    areas = dc.dd.base_pool.resource_cluster
    bases = [unit for unit in self.obs['units']
             if unit.unit_type in BASE_UNITS]
    d_min = 10000
    pos = None
    for area in areas:
      dist = [dist_to_pos(base, area.ideal_base_pos) for base in bases]
      if min(dist) > 5:  # area do not have a base now
        d = dc.dd.base_pool.home_dist[area]
        if 5 < d < d_min:
          pos = area.ideal_base_pos
          d_min = d
    return pos

  def find_base_pos_aggressive(self, dc):
    bases = [unit for unit in self.obs['units']
             if unit.unit_type in BASE_UNITS]
    if len(dc.dd.base_pool.bases) < 4:
      sorted_area = sorted(dc.dd.base_pool.home_dist.items(),
                           key=operator.itemgetter(1))
    else:
      sorted_area = sorted(dc.dd.base_pool.enemy_home_dist.items(),
                           key=operator.itemgetter(1))
      sorted_area = sorted_area[4:]
    sorted_pos_list = [x[0].ideal_base_pos for x in sorted_area]
    for area_pos in sorted_pos_list:
      dist = [dist_to_pos(base, area_pos) for base in bases]
      if min(dist) > 5:  # area do not have a base now
        return area_pos
    return None

  def ideal_harvesters(self, base_item):
    num = base_item.unit.int_attr.ideal_harvesters
    for vb_tag in base_item.vb_set:
      vb = self.find_unit_by_tag(vb_tag)[0]
      num += vb.int_attr.ideal_harvesters
    return num

  def assigned_harvesters(self, base_item):
    num = base_item.unit.int_attr.assigned_harvesters
    for vb_tag in base_item.vb_set:
      vb = self.find_unit_by_tag(vb_tag)[0]
      num += vb.int_attr.assigned_harvesters
    return num

  def should_gas_first(self, dc):
    play_info = self.obs["player"]
    minerals, vespene = play_info[1:3]
    if minerals > 400 and vespene < minerals/3:
      return True
    return False

  def should_mineral_first(self, dc):
    play_info = self.obs["player"]
    minerals, vespene = play_info[1:3]
    if vespene > 300 and minerals < 2 * vespene:
      return True
    return False

  def add_upgrade(self, dc):
    upgrade_list = [UPGRADE_ID.ZERGGROUNDARMORSLEVEL1,
                    UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL1,
                    UPGRADE_ID.CHITINOUSPLATING,
                    UPGRADE_ID.ZERGGROUNDARMORSLEVEL2,
                    UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL2]
    if (distutils.version.LooseVersion(dc.sd.game_version)
        >= distutils.version.LooseVersion('4.1.4')):
      upgrade_list.append(UPGRADE_ID.EVOLVEGROOVEDSPINES)
    upgrade_list.extend([UPGRADE_ID.ZERGGROUNDARMORSLEVEL3,
                         UPGRADE_ID.ZERGMISSILEWEAPONSLEVEL3,
                         UPGRADE_ID.EVOLVEMUSCULARAUGMENTS,
                         UPGRADE_ID.ZERGMELEEWEAPONSLEVEL1,
                         UPGRADE_ID.ZERGMELEEWEAPONSLEVEL2,
                         UPGRADE_ID.ZERGMELEEWEAPONSLEVEL3])

    for upgrade_id in upgrade_list:
      build_item = self.TT.getUpgradeData(upgrade_id.value)
      if (not self.has_building_built(build_item.whatBuilds) or
          not self.has_building_built(build_item.requiredUnits) or
          not self.has_upgrade(dc, build_item.requiredUpgrades)):
        continue
      if self.upgrade_in_progress(upgrade_id.value):
        continue
      if self.has_upgrade(dc, [upgrade_id.value]):
        continue
      else:
        if (upgrade_id not in self.cut_in_item and
            self.find_spare_building(build_item.whatBuilds)):
          self.build_order.queue_as_highest(upgrade_id)
          self.cut_in_item.append(upgrade_id)
          if self.verbose > 0:
            print('Cut in: {}'.format(upgrade_id))
        break

  def find_spare_building(self, unit_type_list):
    for unit_type in unit_type_list:
      units = self.find_unit(unit_type)
      for unit in units:
        if (len(unit.orders) == 0
            and unit.float_attr.build_progress == 1):
          return unit
    return None

  def upgrade(self, build_item, dc):
    builder_list = build_item.whatBuilds
    builder = self.find_spare_building(builder_list)
    if builder is not None:
      dc.dd.build_command_queue.put(
          BuildCmdUpgrade(building_tag=builder.tag,
                          ability_id=build_item.buildAbility))
      return True
    return False
