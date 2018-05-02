from pysc2.lib.typeenums import UNIT_TYPEID
from tstarbot.combat.micro.micro_base import MicroBase
from tstarbot.combat.micro.roach_micro import RoachMgr
from tstarbot.combat.micro.lurker_micro import LurkerMgr
from tstarbot.combat.micro.mutalisk_micro import MutaliskMgr
from tstarbot.combat.micro.ravager_micro import RavagerMgr
from tstarbot.combat.micro.viper_micro import ViperMgr
from tstarbot.combat.micro.corruptor_micro import CorruptorMgr
from tstarbot.combat.micro.infestor_micro import InfestorMgr


class MicroMgr(MicroBase):
    """ A zvz Zerg combat manager """
    def __init__(self):
        super(MicroMgr, self).__init__()
        self.roach_mgr = RoachMgr()
        self.lurker_mgr = LurkerMgr()
        self.mutalisk_mgr = MutaliskMgr()
        self.ravager_mgr = RavagerMgr()
        self.viper_mgr = ViperMgr()
        self.corruptor_mgr = CorruptorMgr()
        self.infestor_mgr = InfestorMgr()

    def exe(self, dc, u, pos, mode):
        if u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_ROACH.value,
                UNIT_TYPEID.ZERG_ROACHBURROWED.value]:
            self.roach_mgr.update(dc)
            action = self.roach_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_LURKERMP.value,
                UNIT_TYPEID.ZERG_LURKERMPBURROWED.value]:
            self.lurker_mgr.update(dc)
            action = self.lurker_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_MUTALISK.value]:
            self.mutalisk_mgr.update(dc)
            action = self.mutalisk_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_RAVAGER.value]:
            self.ravager_mgr.update(dc)
            action = self.ravager_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_VIPER.value]:
            self.viper_mgr.update(dc)
            action = self.viper_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_CORRUPTOR.value]:
            self.corruptor_mgr.update(dc)
            action = self.corruptor_mgr.act(u, pos, mode)
        elif u.int_attr.unit_type in [
                UNIT_TYPEID.ZERG_INFESTOR.value]:
            self.infestor_mgr.update(dc)
            action = self.infestor_mgr.act(u, pos, mode)
        else:
            self.update(dc)
            action = self.default_act(u, pos, mode)
        return action

    def default_act(self, u, pos, mode):
        # if len(self.enemy_combat_units) > 0:
        #     closest_enemy = self.find_closest_enemy(u, self.enemy_combat_units)
        #     if self.is_run_away(u, closest_enemy, self.self_combat_units):
        #         action = self.run_away_from_closest_enemy(u, closest_enemy)
        #     else:
        #         action = self.attack_pos(u, pos)
        # else:
        action = self.attack_pos(u, pos)
        return action

