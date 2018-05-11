"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.lib.typeenums import ABILITY_ID
from s2clientprotocol import sc2api_pb2 as sc_pb
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.combat.micro.micro_mgr import MicroMgr


class BaseCombatMgr(object):
    """ Basic Combat Manager

    Common Utilites for combat are implemented here. """

    def __init__(self, dc):
        pass

    def reset(self):
        pass

    def update(self, dc, am):
        pass

    @staticmethod
    def move_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.MOVE.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    @staticmethod
    def attack_pos(u, pos):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.ATTACK_ATTACK.value
        action.action_raw.unit_command.target_world_space_pos.x = pos['x']
        action.action_raw.unit_command.target_world_space_pos.y = pos['y']
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action


class ZergCombatMgr(BaseCombatMgr):
    """ A zvz Zerg combat manager """
    def __init__(self, dc):
        super(ZergCombatMgr, self).__init__(dc)
        self.dc = dc
        self.micro_mgr = MicroMgr(dc)

    def reset(self):
        self.micro_mgr = MicroMgr(self.dc)
        self.dc = None

    def update(self, dc, am):
        super(ZergCombatMgr, self).update(dc, am)
        self.dc = dc

        actions = list()
        while True:
            cmd = dc.dd.combat_command_queue.pull()
            if not cmd:
                break
            else:
                actions.extend(self.exe_cmd(cmd.squad, cmd.position, cmd.type))
        am.push_actions(actions)

    def exe_cmd(self, squad, pos, mode):
        actions = []
        if mode == CombatCmdType.ATTACK:
            actions = self.exe_attack(squad, pos)
        elif mode == CombatCmdType.MOVE:
            actions = self.exe_move(squad, pos)
        elif mode == CombatCmdType.DEFEND:
            actions = self.exe_defend(squad, pos)
        elif mode == CombatCmdType.RALLY:
            actions = self.exe_rally(squad, pos)
        return actions

    def exe_attack(self, squad, pos):
        actions = list()
        squad_units = []
        for combat_unit in squad.units:
            squad_units.append(combat_unit.unit)
        for u in squad_units:
            if self.micro_mgr is not None:
                action = self.exe_micro(u, pos, mode=CombatCmdType.ATTACK)
            else:
                action = self.attack_pos(u, pos)
            actions.append(action)
        return actions

    def exe_defend(self, squad, pos):
        actions = list()
        squad_units = []
        for combat_unit in squad.units:
            squad_units.append(combat_unit.unit)
        for u in squad_units:
            if self.micro_mgr is not None:
                action = self.exe_micro(u, pos, mode=CombatCmdType.DEFEND)
            else:
                action = self.attack_pos(u, pos)
            actions.append(action)
        return actions

    def exe_move(self, squad, pos):
        actions = []
        for u in squad.units:
            actions.append(self.move_pos(u.unit, pos))
        return actions

    def exe_rally(self, squad, pos):
        actions = []
        for u in squad.units:
            actions.append(self.attack_pos(u.unit, pos))
        return actions

    def exe_micro(self, u, pos, mode):
        action = self.micro_mgr.exe(self.dc, u, pos, mode)
        return action
