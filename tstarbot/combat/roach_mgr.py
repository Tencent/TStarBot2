from pysc2.lib.typeenums import ABILITY_ID
from s2clientprotocol import sc2api_pb2 as sc_pb


class RoachMgr:
    """ A zvz Zerg combat manager """
    def __init__(self):
        pass

    def reset(self):
        pass

    def update(self, dc, am):
        pass

    def burrow_down(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWDOWN.value
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action

    def burrow_up(self, u):
        action = sc_pb.Action()
        action.action_raw.unit_command.ability_id = ABILITY_ID.BURROWUP.value
        action.action_raw.unit_command.unit_tags.append(u.tag)
        return action
