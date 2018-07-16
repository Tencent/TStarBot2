import tensorflow as tf
from gym.spaces import Box, Discrete
from baselines import deepq
from baselines.common.tf_util import load_state
from baselines.deepq.utils import ObservationInput
from baselines.deepq.simple import ActWrapper

from enum import Enum, unique
import numpy as np

import tstarbot.scout.tasks.scout_task as st
from tstarbot.scout.tasks.scout_task import ScoutTask
from tstarbot.data.pool import macro_def as md

MOVE_RANGE = 1.0

@unique
class ScoutMove(Enum):
  UPPER = 0
  LEFT = 1
  DOWN = 2
  RIGHT = 3
  UPPER_LEFT = 4
  LOWER_LEFT = 5
  LOWER_RIGHT = 6
  UPPER_RIGHT = 7
  NOOP = 8
  HOME = 9

class ScoutExploreTaskRL(ScoutTask):
  act = None
  def __init__(self, scout, target, home, model_dir, map_max_x, map_max_y):
    super(ScoutExploreTaskRL, self).__init__(scout, home)
    self._target = target
    self._status = md.ScoutTaskStatus.DOING
    '''
    scout explore task
    Simple64 = 88 * 96
    AbyssalReef = 200 * 176
    Acolyte = 168 * 200
    AscensiontoAiur = 176 * 152
    Frost = 184 * 184
    Interloper = 152 * 176
    MechDepot = 184 * 176
    Odyssey = 168 * 184
    '''
    self._map_max_x = map_max_x
    self._map_max_y = map_max_y
    self._reverse = self.judge_reverse(scout)
    self.load_model(model_dir)

  def type(self):
    return md.ScoutTaskType.EXPORE

  def target(self):
    return self._target

  def post_process(self):
    self._target.has_scout = False
    self._scout.is_doing_task = False
    if self._status == md.ScoutTaskStatus.SCOUT_DESTROY:
      if self._check_in_base_range() and not self._judge_task_done():
        self._target.has_enemy_base = True
        self._target.has_army = True
      else:
        self._target.has_scout = False
        #print('SCOUT explore_task post destory; target=', str(self._target))
    else:
      #print('SCOUT task post_process, status=', self._status, ';target=', str(self._target))
      pass

  @staticmethod
  def load_model(model_path):
    if ScoutExploreTaskRL.act is not None:
      return

    class FakeEnv(object):
      def __init__(self):
        low = np.zeros(6)
        high = np.ones(6)
        self.observation_space = Box(low, high)
        self.action_space = Discrete(8)

    def make_obs_ph(name):
      return ObservationInput(env.observation_space, name=name)
    
    env = FakeEnv()
    network = deepq.models.mlp([64, 32])
    act_params = {
      'make_obs_ph': make_obs_ph,
      'q_func': network,
      'num_actions': env.action_space.n,
    }

    act = deepq.build_act(**act_params)
    sess = tf.Session()
    sess.__enter__()
    print("load_model path=", model_path)
    load_state(model_path)
    ScoutExploreTaskRL.act = ActWrapper(act, act_params)
    print("load_model ok")

  def _do_task_inner(self, view_enemys, dc):
    if self._check_scout_lost():
      self._status = md.ScoutTaskStatus.SCOUT_DESTROY
      return None

    if self.check_end(view_enemys, dc):
      action = ScoutMove.HOME.value
      self._status = md.ScoutTaskStatus.DONE
    else:
      obs = self._get_obs()
      action = ScoutExploreTaskRL.act(obs[None])[0]
    next_pos = self._calcuate_pos_by_action(action)
    return self._move_to_target(next_pos)

  def _get_obs(self):
    scout = self.scout().unit()
    if self._reverse:
      scout_pos = self.pos_transfer(scout.float_attr.pos_x, scout.float_attr.pos_y)
    else:
      scout_pos = (scout.float_attr.pos_x, scout.float_attr.pos_y) 
    return np.array([float(scout_pos[0]) / self._map_max_x,
                     float(scout_pos[1]) / self._map_max_y,
                     float(self._home[0]) / self._map_max_x,
                     float(self._home[1]) / self._map_max_y,
                     float(self._target.pos[0]) / self._map_max_x,
                     float(self._target.pos[1]) / self._map_max_y])

  def _calcuate_pos_by_action(self, action):
    scout = self.scout().unit()
    if self._reverse:
      action = self.action_transfer(action)

    if action == ScoutMove.UPPER.value:
      pos = (scout.float_attr.pos_x,
             scout.float_attr.pos_y + MOVE_RANGE)
      #print('action upper,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.LEFT.value:
      pos = (scout.float_attr.pos_x + MOVE_RANGE,
             scout.float_attr.pos_y)
      #print('action left,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.DOWN.value:
      pos = (scout.float_attr.pos_x,
             scout.float_attr.pos_y - MOVE_RANGE)
      #print('action down,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.RIGHT.value:
      pos = (scout.float_attr.pos_x - MOVE_RANGE,
             scout.float_attr.pos_y)
      #print('action right,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.UPPER_LEFT.value:
      pos = (scout.float_attr.pos_x + MOVE_RANGE,
             scout.float_attr.pos_y + MOVE_RANGE)
      #print('action upper_left,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.LOWER_LEFT.value:
      pos = (scout.float_attr.pos_x + MOVE_RANGE,
             scout.float_attr.pos_y - MOVE_RANGE)
      #print('action lower_left,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.LOWER_RIGHT.value:
      pos = (scout.float_attr.pos_x - MOVE_RANGE,
             scout.float_attr.pos_y - MOVE_RANGE)
      #print('action lower_right,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.UPPER_RIGHT.value:
      pos = (scout.float_attr.pos_x - MOVE_RANGE,
             scout.float_attr.pos_y + MOVE_RANGE)
      #print('action upper_right,scout:{} pos:{}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), pos))
    elif action == ScoutMove.HOME.value:
      print('*** return to home ***, home=', self._home)
      pos = self._home
    else:
      #print('action upper_right,scout:{} pos:None, action={}'.format(
      #       (scout.float_attr.pos_x, scout.float_attr.pos_y), action))
      pos = None
    return pos

  def _check_in_base_range(self):
    dist = md.calculate_distance(self._scout.unit().float_attr.pos_x,
                                 self._scout.unit().float_attr.pos_y,
                                 self._target.pos[0],
                                 self._target.pos[1])
    if dist < st.SCOUT_CRUISE_ARRIVAED_RANGE:
      return True
    else:
      return False

  def _judge_task_done(self):
    if self._target.has_enemy_base:
      return True
    elif self._target.has_army:
      return True
    else:
      return False

  def judge_reverse(self, scout):
    if scout.unit().float_attr.pos_x < scout.unit().float_attr.pos_y:
      return False
    else:
      return True

  def action_transfer(self, action):
    if action == ScoutMove.UPPER.value:
      return ScoutMove.DOWN.value
    elif action == ScoutMove.LEFT.value:
      return ScoutMove.RIGHT.value
    elif action == ScoutMove.DOWN.value:
      return ScoutMove.UPPER.value
    elif action == ScoutMove.RIGHT.value:
      return ScoutMove.LEFT.value
    elif action == ScoutMove.UPPER_LEFT.value:
      return ScoutMove.LOWER_RIGHT.value
    elif action == ScoutMove.LOWER_LEFT.value:
      return ScoutMove.UPPER_RIGHT.value
    elif action == ScoutMove.LOWER_RIGHT.value:
      return ScoutMove.UPPER_LEFT.value
    elif action == ScoutMove.UPPER_RIGHT.value:
      return ScoutMove.LOWER_LEFT.value
    elif action == ScoutMove.HOME.value:
      return action
    else:
      pos = None
    return pos

  def pos_transfer(self, x, y):
    cx = self._map_max_x / 2
    cy = self._map_max_y / 2
    pos_x = 0.0
    pos_y = 0.0
    if x > cx:
      pos_x = cx - abs(x - cx)
    else:
      pos_x = cx + abs(x - cx)

    if y > cy:
      pos_y = cy - abs(y - cy)
    else:
      pos_y = cy + abs(y - cy)

    return (pos_x, pos_y)


