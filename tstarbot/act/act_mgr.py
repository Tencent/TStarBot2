"""Scripted Zerg agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from copy import deepcopy


class ActMgr(object):
  def __init__(self):
    self.cur_actions = []

  def push_actions(self, actions):
    if type(actions == list):
      self.cur_actions += actions
    else:
      self.cur_actions.append(actions)

  def pop_actions(self):
    a = deepcopy(self.cur_actions)
    self.cur_actions = []
    return a
