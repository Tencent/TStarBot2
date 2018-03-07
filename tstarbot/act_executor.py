from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

class ActExecutor:
  def __init__(self, env):
    self._env = env

  def exec_raw(self, pb_actions):
    return self.exec_inner(pb_actions, True)

  def exec_sc2(self, sc2_actions):
    return self.exec_inner(sc2_actions, False)

  def exec_inner(self, actions, raw_flag):
    if raw_flag:
      self._env.set_raw()
      timesteps = self._env.step(actions)
      self._env.reset_raw()
    else:
      timesteps = self._env.step(actions)

    is_end = False
    if timesteps[0].last():
      is_end = True
    return (timesteps, is_end)

