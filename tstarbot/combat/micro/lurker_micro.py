from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID, UPGRADE_ID
from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.combat.micro.micro_base import MicroBase


class LurkerMgr(MicroBase):
    """ A zvz Zerg combat manager """
    def __init__(self):
        super(LurkerMgr, self).__init__()
        self.lurker_range = 9

    @staticmethod
    def burrow_down(u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWDOWN_LURKER.value
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def burrow_up(u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWUP_LURKER.value
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def act(self, u, pos, mode):
        if u.int_attr.unit_type == UNIT_TYPEID.ZERG_LURKERMP.value:
            if len(self.enemy_combat_units) > 0:
                closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)

                if self.cal_square_dist(u, closest_enemy) < self.lurker_range:
                    # print('lurker should burrow down!')
                    action = self.burrow_down(u)
                else:
                    action = self.move_pos(u, pos)
            else:
                action = self.move_pos(u, pos)
        elif u.int_attr.unit_type == UNIT_TYPEID.ZERG_LURKERMPBURROWED.value:
            if len(self.enemy_combat_units) > 0:
                closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)
                if self.cal_square_dist(u, closest_enemy) < self.lurker_range:
                    action = self.attack_pos(u, pos)
                else:
                    # print('lurker should burrow up!')
                    action = self.burrow_up(u)
            else:
                action = self.burrow_up(u)
        else:
            print("Unrecognized roach type: %s" % str(u.int_attr.unit_type))
            raise NotImplementedError
        return action
