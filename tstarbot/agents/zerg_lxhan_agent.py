"""
lxhan
A rule based full game bot focusing on combat module.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.data.demo_dc import ZergLxHanDcMgr
from tstarbot.production.production_mgr import ZergProductionLxHanMgr
from tstarbot.combat.combat_mgr import ZergCombatLxHanMgr
from tstarbot.act.act_mgr import ActMgr
from pysc2.agents import base_agent
from pysc2.lib import stopwatch
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID, ABILITY_ID
from pysc2.lib import actions as pysc2_actions
from pysc2.lib.features import SCREEN_FEATURES
from pysc2.lib.features import MINIMAP_FEATURES
import numpy as np
import random


sw = stopwatch.sw


def micro_select_hatchery(observation, base_pos):
    # unit_type = observation["screen"][SCREEN_FEATURES.unit_type.index]
    # candidate_xy = np.transpose(np.nonzero(unit_type == UNIT_TYPEID.ZERG_HATCHERY.value)).tolist()
    # if len(candidate_xy) == 0: return None
    # screen_xy = random.choice(candidate_xy)

    if base_pos[0] > base_pos[1]:
        xy = [24, 30]
    else:
        xy = [36, 35]

    function_id = pysc2_actions.FUNCTIONS.select_point.id
    function_args = [[0], xy[::-1]]
    return function_id, function_args


def micro_select_larvas(observation):
    function_id = pysc2_actions.FUNCTIONS.select_larva.id
    function_args = []
    return function_id, function_args


def check_larva_selected(observation):
    unit_type_list = observation["multi_select"][:, 0]
    if UNIT_TYPEID.ZERG_LARVA.value not in unit_type_list:
        return False
    else:
        return True


class ZergLxHanAgent(base_agent.BaseAgent):
    """ An agent for full game focusing on Combat module.
    All production and resource functions are squeezed in ResourceMgr
    High level rule: 3 bases + roaches + hydralisk.
    """

    def __init__(self):
        super(ZergLxHanAgent, self).__init__()
        self.obs_mgr = ZergLxHanDcMgr()
        self.resource_mgr = ZergProductionLxHanMgr()
        self.combat_mgr = ZergCombatLxHanMgr()
        self.act_mgr = ActMgr()

        self.episode_step = 0
        self.is_larva_selected = 0
        self.is_base_selected = 0

    def reset(self):
        self.resource_mgr.reset()
        self.combat_mgr.reset()
        self.obs_mgr.reset()
        self.episode_step = 0

    def step(self, timestep):
        super(ZergLxHanAgent, self).step(timestep)
        return self.mystep(timestep)

    @sw.decorate
    def mystep(self, timestep):
        # There exists some bug in mac os's game core that if larvas are not selected the env will crush; here gives a
        # temporal solution that using pysc2 action to select larvas first, but the bug needs to be fixed.
        IF_YOU_USE_MAC = True
        if IF_YOU_USE_MAC:
            if self.episode_step == 0:
                self.obs_mgr.update(timestep=timestep)
                actions = self.act_mgr.pop_actions()
            else:
                if not check_larva_selected(timestep.observation) and self.is_base_selected == 0:
                    self.is_larva_selected = 0

                if self.is_larva_selected == 0:
                    if self.is_base_selected == 0:
                        action = micro_select_hatchery(timestep.observation, self.obs_mgr.base_pos)
                        self.is_base_selected = 1
                    else:
                        action = micro_select_larvas(timestep.observation)
                        self.is_base_selected = 0
                        self.is_larva_selected = 1
                    if action is None or action[0] not in timestep.observation["available_actions"]:
                        actions = []
                    else:
                        actions = pysc2_actions.FunctionCall(*action)
                else:
                    actions = self.procedure(timestep)
        else:
            actions = self.procedure(timestep)

        self.episode_step += 1
        return actions

    def procedure(self, timestep):
        with sw('obs_mgr'):
            self.obs_mgr.update(timestep=timestep)
        with sw('str_mgr'):
            pass
            # self.strategy_mgr.update(self.obs_mgr, self.act_mgr)
        with sw('pro_mgr'):
            pass
            # self.production_mgr.update(self.obs_mgr, self.act_mgr)
        with sw('bud_mgr'):
            # self.building_mgr.update(self.obs_mgr, self.act_mgr)
            pass
        with sw('res_mgr'):
            self.resource_mgr.update(self.obs_mgr, self.act_mgr)
        with sw('com_mgr'):
            self.combat_mgr.update(self.obs_mgr, self.act_mgr)
        with sw('act_mgr'):
            actions = self.act_mgr.pop_actions()

        return actions
