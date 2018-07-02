from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import ABILITY_ID
from s2clientprotocol import sc2api_pb2 as sc_pb

from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.pool.macro_def import AIR_UNITS


class LurkerMgr(MicroBase):
  """ A zvz Zerg combat manager """

  def __init__(self):
    super(LurkerMgr, self).__init__()
    self.lurker_range = 9

  @staticmethod
  def burrow_down(u):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = \
      ABILITY_ID.BURROWDOWN_LURKER.value
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  @staticmethod
  def burrow_up(u):
    action = sc_pb.Action()
    action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWUP_LURKER.value
    action.action_raw.unit_command.unit_tags.append(u.tag)
    return action

  def act(self, u, pos, mode):
    lurker_can_atk_units = [e for e in self.enemy_units
                            if e.int_attr.unit_type not in AIR_UNITS]
    if u.int_attr.unit_type == UNIT_TYPEID.ZERG_LURKERMP.value:
      if len(lurker_can_atk_units) > 0:
        closest_enemy = self.find_closest_enemy(u, lurker_can_atk_units)

        if self.dist_between_units(u, closest_enemy) < self.lurker_range:
          action = self.burrow_down(u)
        else:
          action = self.move_pos(u, pos)
      else:
        action = self.move_pos(u, pos)
    elif u.int_attr.unit_type == UNIT_TYPEID.ZERG_LURKERMPBURROWED.value:
      if len(lurker_can_atk_units) > 0:
        closest_enemy = self.find_closest_enemy(u, lurker_can_atk_units)
        if self.dist_between_units(u, closest_enemy) < self.lurker_range:
          action = self.attack_pos(u, pos)
        else:
          action = self.burrow_up(u)
      else:
        action = self.burrow_up(u)
    else:
      print("Unrecognized lurker type: %s" % str(u.int_attr.unit_type))
      raise NotImplementedError
    return action
