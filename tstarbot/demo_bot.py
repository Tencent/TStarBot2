from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
import random

from pysc2.lib import actions
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib import actions
import tstarbot as ts

UNIT_TYPE_HATCHERY = 86
UNIT_TYPE_DRONE= 104

class DemoPool(ts.PoolBase):
  def __init__(self):
    self._drone_ids = []
    self._hatcherys = []

  def update(self, obs):
    units = obs['units']
    self._locate_hatcherys(units)
    self._update_drone(units)

  def _locate_hatcherys(self, units):
    for u in units:
      if u.unit_type == UNIT_TYPE_HATCHERY:
        self._hatcherys.append((u.float_attr.pos_x, u.float_attr.pos_y, u.float_attr.pos_z))

  def _update_drone(self, units):
    drone_ids = []
    for u in units:
      if u.unit_type == UNIT_TYPE_DRONE:
        drone_ids.append(u.tag)

    self._drone_ids = drone_ids

  def get_drones(self):
    return self._drone_ids

  def get_hatcherys(self):
    return self._hatcherys

class DemoManager(ts.ManagerBase):
  def __init__(self, pool):
    self._pool = pool
    self._range_high = 5
    self._range_low = -5
    self._move_ability = 1

  def execute(self):
    drone_ids = self._pool.get_drones()
    pos = self._pool.get_hatcherys()
    print('pos=', pos)
    actions = self.move_drone_random_round_hatchery(drone_ids, pos[0])
    return actions

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

class DemoBot:
  """A random agent for starcraft."""
  def __init__(self, env):
    self._pools = []
    self._managers = []
    self._env = env

  def setup(self):
    demo_pool = DemoPool()
    demo_manager = DemoManager(demo_pool)
    self._pools.append(demo_pool)
    self._managers.append(demo_manager)
    self._executor = ts.ActExecutor(self._env)

  def reset(self):
    timesteps = self._env.reset()
    return timesteps

  def run(self, n):
    return self._run_inner(n)

  def _run_inner(self, n):
    try:
      """episode loop """
      step_num = 0
      timesteps = self.reset()
      while True:
        obs = timesteps[0].observation
        for pool in self._pools:
          pool.update(obs)

        actions = [] 
        for manager in self._managers:
          part_actions = manager.execute()
          actions.extend(part_actions)

        result = self._executor.exec_raw(actions)
        if result[1]:
          break
        timesteps = result[0]

        if step_num > n:
          break
        step_num += 1
    except KeyboardInterrupt:
      print("SC2Imp exception")

