from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

class PoolBase(object):
  def update(self, obs):
    raise NotImplementedError

class ManagerBase(object):
  def execute(self):
    raise NotImplementedError

