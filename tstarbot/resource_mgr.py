"""Resource Manager"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
from s2clientprotocol import sc2api_pb2 as sc_pb


class BaseResourceMgr:
    def __init__(self):
        pass

    def update(self, obs_mgr, act_mgr):
        pass


class DancingDronesResourceMgr(BaseResourceMgr):
    def __init__(self):
        super(DancingDronesResourceMgr, self).__init__()
        self._range_high = 5
        self._range_low = -5
        self._move_ability = 1

    def update(self, obs_mgr, act_mgr):
        super(DancingDronesResourceMgr, self).update(obs_mgr, act_mgr)

        drone_ids = obs_mgr.get_drones()
        pos = obs_mgr.get_hatcherys()

        print('pos=', pos)
        actions = self.move_drone_random_round_hatchery(drone_ids, pos[0])

        act_mgr.push_actions(actions)

    def move_drone_random_round_hatchery(self, drone_ids, pos):
        length = len(drone_ids)
        actions = []
        for drone in drone_ids:
            action = sc_pb.Action()
            action.action_raw.unit_command.ability_id = self._move_ability
            x = pos[0] + random.randint(self._range_low, self._range_high)
            y = pos[1] + random.randint(self._range_low, self._range_high)
            action.action_raw.unit_command.target_world_space_pos.x = x
            action.action_raw.unit_command.target_world_space_pos.y = y
            action.action_raw.unit_command.unit_tags.append(drone)
            actions.append(action)
        return actions


class ZergResourceMgr(BaseResourceMgr):
    def __init__(self):
        super(ZergResourceMgr, self).__init__()

    def update(self, obs_mgr, act_mgr):
        super(ZergResourceMgr, self).__init__()

        actions = []

        # TODO: imple here

        act_mgr.push_actions(actions)
