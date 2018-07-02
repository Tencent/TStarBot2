from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.agents import base_agent

from tstarbot.combat.micro.micro_mgr import MicroBase


ROACH_ATTACK_RANGE = 5.0


class DefeatRoachesCombatMgr(base_agent.BaseAgent):
  """ Combat Manager for the DefeatRoaches minimap"""

  def __init__(self):
    super(DefeatRoachesCombatMgr, self).__init__()
    self.marines = None
    self.roaches = None
    self.micro_base = MicroBase()

  def update(self, dc, am):
    self.marines = dc.marines
    self.roaches = dc.roaches

    actions = list()
    for m in self.marines:
      closest_roach = self.micro_base.find_closest_enemy(m, self.roaches)
      closest_enemy_dist = self.micro_base.dist_between_units(m, closest_roach)
      if closest_enemy_dist < ROACH_ATTACK_RANGE and \
              (m.float_attr.health / m.float_attr.health_max) < 0.3 and \
              self.micro_base.find_strongest_unit_hp(self.marines) > 0.9:
        action = self.micro_base.run_away_from_closest_enemy(m, closest_roach,
                                                             0.4)
      else:
        action = self.micro_base.attack_weakest_enemy(m, self.roaches)
      actions.append(action)

    am.push_actions(actions)
