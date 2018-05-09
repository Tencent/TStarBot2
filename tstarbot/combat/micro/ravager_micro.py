from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, UPGRADE_ID
from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.data.pool.macro_def import COMBAT_ANTI_AIR_UNITS

import numpy as np


class RavagerMgr(MicroBase):
    """ A zvz Zerg combat manager """
    def __init__(self):
        super(RavagerMgr, self).__init__()
        self.corrosive_range = 15
        self.corrosive_harm_range = 3

    @staticmethod
    def corrosive_attack_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.EFFECT_CORROSIVEBILE.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def find_densest_enemy_pos_in_range(self, u):
        targets = self.find_units_wihtin_range(u, self.enemy_combat_units, r=self.corrosive_range)
        if len(targets) == 0:
            return None
        target_density = list()
        for e in targets:
            target_density.append(len(self.find_units_wihtin_range(e, targets, r=self.corrosive_harm_range)))
        target_id = np.argmax(target_density)
        target = targets[target_id]
        target_pos = {'x': target.float_attr.pos_x,
                      'y': target.float_attr.pos_y}
        return target_pos

    def act(self, u, pos, mode):
        if u.float_attr.weapon_cooldown > 0:
            target_pos = self.find_densest_enemy_pos_in_range(u)
            if target_pos is None:
                action = self.attack_pos(u, pos)
            else:
                # print('ravager fire!')
                action = self.corrosive_attack_pos(u, target_pos)
        else:
            action = self.attack_pos(u, pos)
        return action
