"""Combat Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.data.pool.macro_def import UNIT_TYPEID
from tstarbot.data.queue.combat_command_queue import CombatCmdType
from tstarbot.combat.micro.micro_mgr import MicroMgr
from tstarbot.combat.micro.lurker_micro import LurkerMgr
import tstarbot.util.geom as geom


class BaseCombatMgr(object):
  """ Basic Combat Manager

  Common Utilites for combat are implemented here. """

  def __init__(self, dc):
    pass

  def reset(self):
    pass

  def update(self, dc, am):
    pass


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
    elif mode == CombatCmdType.ROCK:
      actions = self.exe_rock(squad, pos)
    return actions

  def exe_attack(self, squad, pos):
    actions = list()
    squad_units = []
    for combat_unit in squad.units:
      squad_units.append(combat_unit.unit)
    for u in squad_units:
      action = self.exe_micro(u, pos, mode=CombatCmdType.ATTACK)
      actions.append(action)
    return actions

  def exe_defend(self, squad, pos):
    actions = list()
    squad_units = []
    for combat_unit in squad.units:
      squad_units.append(combat_unit.unit)
    for u in squad_units:
      action = self.exe_micro(u, pos, mode=CombatCmdType.DEFEND)
      actions.append(action)
    return actions

  def exe_move(self, squad, pos):
    actions = []
    for u in squad.units:
      u = u.unit
      if u.int_attr.unit_type == UNIT_TYPEID.ZERG_LURKERMPBURROWED.value:
        actions.append(LurkerMgr().burrow_up(u))
      else:
        actions.append(self.micro_mgr.move_pos(u, pos))
    return actions

  def exe_rally(self, squad, pos):
    actions = []
    for u in squad.units:
      actions.append(self.micro_mgr.attack_pos(u.unit, pos))
    return actions

  def exe_rock(self, squad, pos):
    actions = []
    rocks = [u for u in self.dc.sd.obs['units']
             if u.int_attr.unit_type ==
             UNIT_TYPEID.NEUTRAL_DESTRUCTIBLEROCKEX1DIAGONALHUGEBLUR.value]
    target_rock = None
    for r in rocks:
      d = geom.dist_to_pos(r, (pos['x'], pos['y']))
      if d < 0.1:
        target_rock = r
        break
    for u in squad.units:
      actions.append(self.micro_mgr.attack_target(u, target_rock))
    return actions

  def exe_micro(self, u, pos, mode):
    action = self.micro_mgr.exe(self.dc, u, pos, mode)
    return action
