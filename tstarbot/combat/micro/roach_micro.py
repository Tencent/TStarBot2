from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, UPGRADE_ID

from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.pool.macro_def import UNITS_CAN_DETECT


class RoachMgr(MicroBase):
  """ A zvz Zerg combat manager """

  def __init__(self):
    super(RoachMgr, self).__init__()
    self.overseer_sight = 15

  @staticmethod
  def burrow_down(u):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWDOWN.value
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  @staticmethod
  def burrow_up(u):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWUP.value
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  def act(self, u, pos, mode):
    if u.int_attr.unit_type == UNIT_TYPEID.ZERG_ROACH.value:
      # hit and burrow/run
      closest_enemy_dist = 100000
      if len(self.enemy_combat_units) > 0:
        closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)
        closest_enemy_dist = self.dist_between_units(closest_enemy, u)

        if self.is_run_away(u, closest_enemy, self.self_combat_units):
          if UPGRADE_ID.BURROW.value in self.dc.sd.obs[
            'raw_data'].player.upgrade_ids:
            action = self.burrow_down(u)
          else:
            action = self.run_away_from_closest_enemy(u, closest_enemy)
        else:
          action = self.attack_pos(u, pos)
      else:
        action = self.attack_pos(u, pos)
      # burrow to recover when idle
      if (u.float_attr.health / u.float_attr.health_max < 1 and
              closest_enemy_dist > 1.2 * self.roach_attack_range):
        action = self.burrow_down(u)
    elif u.int_attr.unit_type == UNIT_TYPEID.ZERG_ROACHBURROWED.value:
      if u.float_attr.health / u.float_attr.health_max == 1:
        action = self.burrow_up(u)
      else:
        action = self.hold_fire(u)
        if len(self.enemy_combat_units) > 0:
          closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)
          if (self.is_run_away(u, closest_enemy, self.self_combat_units) and
                  UPGRADE_ID.TUNNELINGCLAWS.value in self.dc.sd.obs[
                  'raw_data'].player.upgrade_ids):
            action = self.run_away_from_closest_enemy(u, closest_enemy)

        # if detected
        # print(u.int_attr.cloak)
        enemy_detect_units = [u for u in self.enemy_units
                              if u.int_attr.unit_type in UNITS_CAN_DETECT]
        if len(enemy_detect_units) > 0 and len(self.enemy_combat_units) > 0:
          closest_enemy_detect_unit = \
            self.find_closest_enemy(u, enemy_detect_units)
          closest_enemy_combat_unit = \
            self.find_closest_enemy(u, self.enemy_combat_units)
          if self.dist_between_units(closest_enemy_detect_unit,
                                     u) < self.overseer_sight:
            action = self.run_away_from_closest_enemy(u,
                                                      closest_enemy_combat_unit)
    else:
      print("Unrecognized roach type: %s" % str(u.int_attr.unit_type))
      raise NotImplementedError
    return action
