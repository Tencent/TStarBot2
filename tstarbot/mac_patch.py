from pysc2.lib.typeenums import UNIT_TYPEID
from pysc2.lib import actions as pysc2_actions
from pysc2.lib.features import SCREEN_FEATURES
import random
import numpy as np


def micro_select_hatchery(observation):
    unit_type = observation["screen"][SCREEN_FEATURES.unit_type.index]
    candidate_xy = np.transpose(np.nonzero(unit_type == UNIT_TYPEID.ZERG_HATCHERY.value)).tolist()
    if len(candidate_xy) == 0:
        return None
    xy = np.asarray(candidate_xy).mean(axis=0)

    function_id = pysc2_actions.FUNCTIONS.select_point.id
    function_args = [[0], xy[::-1]]
    return function_id, function_args


def micro_group_selected(observation, g_id):
    function_id = pysc2_actions.FUNCTIONS.select_control_group.id
    function_args = [[1], [g_id]]
    return function_id, function_args


def micro_recall_selected_group(observation, g_id):
    function_id = pysc2_actions.FUNCTIONS.select_control_group.id
    function_args = [[0], [g_id]]
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
