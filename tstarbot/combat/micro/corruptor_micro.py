from pysc2.lib.typeenums import ABILITY_ID
from s2clientprotocol import sc2api_pb2 as sc_pb

from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.pool.macro_def import COMBAT_FLYING_UNITS


class CorruptorMgr(MicroBase):
  """ A zvz Zerg combat manager """

  def __init__(self):
    super(CorruptorMgr, self).__init__()
    self.corruptor_range = 20

  @staticmethod
  def parasitic_bomb_attack_target(u, target):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
      ABILITY_ID.EFFECT_PARASITICBOMB.value
    action.action_raw.unit_command.target_unit_tag = target.tag
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  def act(self, u, pos, mode):
    air_targets = [e for e in self.enemy_combat_units
                   if e.int_attr.unit_type in COMBAT_FLYING_UNITS]
    if len(air_targets) > 0:
      closest_target = self.find_closest_enemy(u, air_targets)
      if self.dist_between_units(u, closest_target) > self.corruptor_range:
        # follow the ground unit
        self_ground_units = [u for u in self.self_combat_units
                             if u.int_attr.unit_type not in COMBAT_FLYING_UNITS]
        if len(self_ground_units) == 0:
          print('no ground units')
          action = self.hold_fire(u)
          return action
        self_most_dangerous_ground_unit = self.find_closest_units_in_battle(
          self_ground_units, closest_target)
        move_pos = {'x': self_most_dangerous_ground_unit.float_attr.pos_x,
                    'y': self_most_dangerous_ground_unit.float_attr.pos_y}
        action = self.move_pos(u, move_pos)
      else:
        # attack
        action = self.attack_pos(u, pos)
    else:
      move_pos = self.get_center_of_units(self.self_combat_units)
      action = self.move_pos(u, move_pos)
    return action
