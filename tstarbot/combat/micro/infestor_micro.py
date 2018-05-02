from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, UPGRADE_ID
from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.pool.macro_def import COMBAT_ANTI_AIR_UNITS, COMBAT_FLYING_UNITS

import numpy as np


class InfestorMgr(MicroBase):
    """ A zvz Zerg combat manager """
    def __init__(self):
        super(InfestorMgr, self).__init__()
        self.infestor_range = 20

    @staticmethod
    def fungal_growth_attack_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.EFFECT_FUNGALGROWTH.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def find_densest_enemy_pos_in_range(self, u):
        enemy_ground_units = [u for u in self.enemy_combat_units
                              if u.int_attr.unit_type not in COMBAT_FLYING_UNITS and
                              u.int_attr.unit_type not in [UNIT_TYPEID.ZERG_SPINECRAWLER.value,
                                                           UNIT_TYPEID.ZERG_SPORECRAWLER.value]]
        targets = self.find_units_wihtin_range(u, enemy_ground_units, r=self.infestor_range)
        if len(targets) == 0:
            return None
        target_density = list()
        for e in targets:
            target_density.append(len(self.find_units_wihtin_range(e, targets, r=self.viper_harm_range)))
        target_id = np.argmax(target_density)
        target = targets[target_id]
        target_pos = {'x': target.float_attr.pos_x,
                      'y': target.float_attr.pos_y}
        return target_pos

    def act(self, u, pos, mode):
        ground_targets = [e for e in self.enemy_combat_units
                          if e.int_attr.unit_type not in COMBAT_FLYING_UNITS]
        if len(ground_targets) > 0:
            closest_target = self.find_closest_enemy(u, ground_targets)
            if self.cal_square_dist(u, closest_target) < self.infestor_range:
                if u.float_attr.energy > 75:
                    target_pos = self.find_densest_enemy_pos_in_range(u)
                    if target_pos is None:
                        action = self.attack_pos(u, pos)
                        return action
                    action = self.fungal_growth_attack_pos(u, target_pos)
                else:
                    bases = self.dc.dd.base_pool.bases
                    base_units = [bases[tag].unit for tag in bases]
                    closest_base = self.find_closest_enemy(u, base_units)
                    base_pos = {'x': closest_base.float_attr.pos_x,
                                'y': closest_base.float_attr.pos_y}
                    action = self.move_pos(u, base_pos)
            else:
                action = self.attack_pos(u, pos)
        else:
            move_pos = self.get_center_of_units(self.self_combat_units)
            action = self.move_pos(u, move_pos)
        return action
