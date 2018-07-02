import pysc2.lib.typeenums as tp

from tstarbot.data.pool.pool_base import PoolBase


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
        tmp_hatcherys.append(
          (u.float_attr.pos_x, u.float_attr.pos_y, u.float_attr.pos_z))
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


class ZergLxHanDcMgr(PoolBase):
  """ full game with Simple64 by producing roaches + hydralisk
  (for testing combat module) """

  def __init__(self):
    super(ZergLxHanDcMgr, self).__init__()
    self.reset()

  def reset(self):
    self.units = []
    self.screen = []
    self.player_info = []

    self.drones = []
    self.hatcheries = []
    self.minerals = []
    self.larvas = []
    self.queen = []
    self.spawningpool = []
    self.extractors = []
    self.vespens = []
    self.roachwarren = []
    self.roaches = []
    self.hydraliskden = []
    self.hydralisk = []

    self.enemy_units = []

    self.base_pos = []
    self.mini_map = []

  def update(self, timestep):
    units = timestep.observation['units']
    screen = timestep.observation['screen']
    player_info = timestep.observation['player']
    mini_map = timestep.observation['minimap']

    self.units = units
    self.screen = screen
    self.player_info = player_info
    self.mini_map = mini_map

    self.collect_drones(units)
    self.collect_hatcheries(units)
    self.collect_minerals(units)
    self.collect_larvas(units)
    self.collect_queen(units)
    self.collect_spawningpool(units)
    self.collect_extractor(units)
    self.collect_vespen(units)
    self.collect_roachwarren(units)
    self.collect_roaches(units)
    self.collect_hydraliskden(units)
    self.collect_hydralisk(units)

    self.collect_enemy_units(units)

    if len(self.hatcheries) != 0 and len(self.base_pos) == 0:
      self.base_pos = [self.hatcheries[0].float_attr.pos_x,
                       self.hatcheries[0].float_attr.pos_y]
      print('base_pos: ', self.base_pos)

  def collect_drones(self, units):
    drones = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_DRONE.value and
          u.int_attr.owner == 1):
        drones.append(u)
    self.drones = drones

  def collect_hatcheries(self, units):
    hatcheries = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_HATCHERY.value and
          u.int_attr.owner == 1):
        hatcheries.append(u)
    self.hatcheries = hatcheries

  def collect_minerals(self, units):
    minerals = []
    for u in units:
      if u.unit_type == tp.UNIT_TYPEID.NEUTRAL_MINERALFIELD.value:
        minerals.append(u)
    self.minerals = minerals

  def collect_larvas(self, units):
    larvas = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_LARVA.value and
          u.int_attr.owner == 1):
        larvas.append(u)
    self.larvas = larvas

  def collect_queen(self, units):
    queen = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_QUEEN.value and
          u.int_attr.owner == 1):
        queen.append(u)
    self.queen = queen

  def collect_spawningpool(self, units):
    spawningpool = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_SPAWNINGPOOL.value and
          u.int_attr.owner == 1):
        spawningpool.append(u)
    self.spawningpool = spawningpool

  def collect_extractor(self, units):
    extractors = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_EXTRACTOR.value and
          u.int_attr.owner == 1):
        extractors.append(u)
    self.extractors = extractors

  def collect_vespen(self, units):
    vespens = []
    for u in units:
      if u.unit_type == tp.UNIT_TYPEID.NEUTRAL_VESPENEGEYSER.value:
        vespens.append(u)
    self.vespens = vespens

  def collect_roachwarren(self, units):
    roachwarren = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_ROACHWARREN.value and
          u.int_attr.owner == 1):
        roachwarren.append(u)
    self.roachwarren = roachwarren

  def collect_roaches(self, units):
    roaches = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_ROACH.value and
          u.int_attr.owner == 1):
        roaches.append(u)
    self.roaches = roaches

  def collect_hydraliskden(self, units):
    hydraliskden = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_HYDRALISKDEN.value and
          u.int_attr.owner == 1):
        hydraliskden.append(u)
    self.hydraliskden = hydraliskden

  def collect_hydralisk(self, units):
    hydralisk = []
    for u in units:
      if (u.unit_type == tp.UNIT_TYPEID.ZERG_HYDRALISK.value and
          u.int_attr.owner == 1):
        hydralisk.append(u)
    self.hydralisk = hydralisk

  def collect_enemy_units(self, units):
    enemy_units = []
    for u in units:
      if u.int_attr.owner == 2:
        enemy_units.append(u)
    self.enemy_units = enemy_units

  def get_drones(self):
    return self.drones

  def get_hatcheries(self):
    return self.hatcheries

  def get_minerals(self):
    return self.minerals

  def get_larvas(self):
    return self.larvas

  def get_queen(self):
    return self.queen

  def get_spawningpool(self):
    return self.spawningpool

  def get_extractor(self):
    return self.extractors

  def get_vespens(self):
    return self.vespens

  def get_roachwarren(self):
    return self.roachwarren

  def get_roaches(self):
    return self.roaches

  def get_hydraliskden(self):
    return self.hydraliskden

  def get_hydralisk(self):
    return self.hydralisk

  def get_enemy_units(self):
    return self.enemy_units
