import numpy as np
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, UPGRADE_ID
from s2clientprotocol import sc2api_pb2 as sc_pb

from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.pool.macro_def import COMBAT_ANTI_AIR_UNITS
from tstarbot.data.pool.macro_def import COMBAT_FLYING_UNITS


class ViperMgr(MicroBase):
  """ A zvz Zerg combat manager """

  def __init__(self):
    super(ViperMgr, self).__init__()
    self.viper_range = 20
    self.viper_harm_range = 3
    self.viper_consume_range = 5

  @staticmethod
  def blinding_cloud_attack_pos(u, pos):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
      ABILITY_ID.EFFECT_BLINDINGCLOUD.value
    action.action_raw.unit_command.target_world_space_pos.x = pos['x']
    action.action_raw.unit_command.target_world_space_pos.y = pos['y']
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  @staticmethod
  def parasitic_bomb_attack_target(u, target):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
      ABILITY_ID.EFFECT_PARASITICBOMB.value
    action.action_raw.unit_command.target_unit_tag = target.tag
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  @staticmethod
  def consume_target(u, target):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
      ABILITY_ID.EFFECT_VIPERCONSUME.value
    action.action_raw.unit_command.target_unit_tag = target.tag
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  def find_densest_enemy_pos_in_range(self, u):
    enemy_ground_units = [e for e in self.enemy_combat_units
                          if e.int_attr.unit_type not in COMBAT_FLYING_UNITS and
                          e.int_attr.unit_type not in [
                            UNIT_TYPEID.ZERG_SPINECRAWLER.value,
                            UNIT_TYPEID.ZERG_SPORECRAWLER.value]]
    targets = self.find_units_wihtin_range(u, enemy_ground_units,
                                           r=self.viper_range)
    if len(targets) == 0:
      return None
    target_density = list()
    for e in targets:
      target_density.append(
        len(self.find_units_wihtin_range(e, targets, r=self.viper_harm_range)))
    target_id = np.argmax(target_density)
    target = targets[target_id]
    target_pos = {'x': target.float_attr.pos_x,
                  'y': target.float_attr.pos_y}
    return target_pos

  def find_densest_air_enemy_unit_in_range(self, u):
    enemy_combat_flying_units = [e for e in self.enemy_combat_units
                                 if e.int_attr.unit_type in COMBAT_FLYING_UNITS]
    if len(enemy_combat_flying_units) == 0:
      return None
    targets = self.find_units_wihtin_range(u, enemy_combat_flying_units,
                                           r=self.viper_range)
    if len(targets) == 0:
      return None
    target_density = list()
    for e in targets:
      target_density.append(
        len(self.find_units_wihtin_range(e, targets, r=self.viper_harm_range)))
    target_id = np.argmax(target_density)
    target = targets[target_id]
    return target

  def act(self, u, pos, mode):
    if len(self.enemy_combat_units) > 0:
      if ((len(u.orders) == 0 or u.orders[
        0].ability_id != ABILITY_ID.EFFECT_VIPERCONSUME.value) and
          u.float_attr.energy > 100):
        # enough energy
        closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)
        # follow the ground unit
        self_ground_units = [a for a in self.self_combat_units
                             if a.int_attr.unit_type not in COMBAT_FLYING_UNITS]
        if len(self_ground_units) == 0:
          action = self.hold_fire(u)
          return action
        self_most_dangerous_ground_unit = self.find_closest_units_in_battle(
          self_ground_units, closest_enemy)
        pos = {'x': self_most_dangerous_ground_unit.float_attr.pos_x,
               'y': self_most_dangerous_ground_unit.float_attr.pos_y}
        action = self.move_pos(u, pos)
        if self.dist_between_units(u, closest_enemy) <= self.viper_range:
          # use bomb
          air_target = self.find_densest_air_enemy_unit_in_range(u)
          if air_target is None:
            # print('use blind')
            ground_pos = self.find_densest_enemy_pos_in_range(u)
            if ground_pos is not None:
              action = self.blinding_cloud_attack_pos(u, ground_pos)
          else:
            # print('use bomb')
            action = self.parasitic_bomb_attack_target(u, air_target)
      else:
        # not enough energy
        # print('not enough energy')
        bases = self.dc.dd.base_pool.bases
        base_units = [bases[tag].unit for tag in bases
                      if bases[tag].unit.float_attr.health > 500
                      and bases[tag].unit.float_attr.build_progress == 1]
        closest_base = self.find_closest_enemy(u, base_units)
        if self.dist_between_units(u, closest_base) < self.viper_consume_range:
          action = self.consume_target(u, closest_base)
        else:
          pos = {'x': closest_base.float_attr.pos_x,
                 'y': closest_base.float_attr.pos_y}
          action = self.move_pos(u, pos)
    else:
      pos = self.get_center_of_units(self.self_combat_units)
      action = self.move_pos(u, pos)
    return action
