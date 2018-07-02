""" sc_pb action utilities """
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib.typeenums import ABILITY_ID


def act_build_by_self(builder_tag, ability_id):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = ability_id
  action.action_raw.unit_command.unit_tags.append(builder_tag)
  return action


def act_build_by_tag(builder_tag, target_tag, ability_id):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = ability_id
  action.action_raw.unit_command.target_unit_tag = target_tag
  action.action_raw.unit_command.unit_tags.append(builder_tag)
  return action


def act_build_by_pos(builder_tag, target_pos, ability_id):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = ability_id
  action.action_raw.unit_command.target_world_space_pos.x = target_pos[0]
  action.action_raw.unit_command.target_world_space_pos.y = target_pos[1]
  action.action_raw.unit_command.unit_tags.append(builder_tag)
  return action


def act_move_to_pos(unit_tag, target_pos):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = ABILITY_ID.MOVE.value
  action.action_raw.unit_command.target_world_space_pos.x = target_pos[0]
  action.action_raw.unit_command.target_world_space_pos.y = target_pos[1]
  action.action_raw.unit_command.unit_tags.append(unit_tag)
  return action


def act_worker_harvests_on_target(target_tag, worker_tag):
  # The CALLER should assure the target-worker is a reasonable pair
  # e.g., the target is an extractor, a mineral,
  # the worker should not be too far away to the target
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = \
    ABILITY_ID.HARVEST_GATHER_DRONE.value
  action.action_raw.unit_command.target_unit_tag = target_tag
  action.action_raw.unit_command.unit_tags.append(worker_tag)
  return action


def act_rally_worker(target_tag, base_tag):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = \
    ABILITY_ID.RALLY_HATCHERY_WORKERS.value
  action.action_raw.unit_command.target_unit_tag = target_tag
  action.action_raw.unit_command.unit_tags.append(base_tag)
  return action


def act_stop(unit_tag):
  action = sc_pb.Action()
  action.action_raw.unit_command.ability_id = ABILITY_ID.STOP.value
  action.action_raw.unit_command.unit_tags.append(unit_tag)
  return action
