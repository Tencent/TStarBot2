from enum import Enum, unique

@unique
class WorkerState(Enum):
  IDLE = 0
  MINERALS = 1
  GAS = 2
  BUILD = 3
  COMBAT = 4
  MOVE = 5
  SCOUT = 6
  REPAIR = 7
  DEFAULT = 8

WORKER_UNITS = set([104])
WORKER_RESOURCE_ABILITY = set([1183, 1184])

class ZergWorkerPool(object):
  def __init__(self):
    """the format of workers is {uid: (unit,state),... }"""
    self._workers = {}
    """the format of idles is set([uid, uid, ....])"""
    self._worker_idle = set([])
    self._worker_minieral = set([])
    self._worker_gas = set([])
    self._worker_build = set([])
    self._worker_tmpjob = set([])

  def assign_gas(self, u):
    if u.tag in self._workers:
      self._update_gas_worker(u)
    else:
      self._add_gas_worker(u)

  def update(self, units):
    new_tags = set([])
    for u in units:
      if self._check_worker(u):
        self._update(u)
        input_tags.add(u.tag)

    union_tags = set(self._workers.keys())
    del_units = union_tags.difference(new_tags)
    for u in del_units:
      self._remove_worker(u)

  def get_idle_workers(self):
    idles = []
    for uid in self._worker_idle:
      idles.append(self._workers[uid])
    return idles

  def get_minieral_workers(self):
    minierals = []
    for uid in self._worker_minieral:
      minierals.append(self._workers[uid])
    return minierals

  def get_gas_workers(self):
    gass = []
    for uid in self._worker_gas:
      gass.append(self._workers[uid])
    return gass

  def get_build_workers(self):
    builds = []
    for uid in self._worker_build:
      builds.append(self._workers[uid])
    return builds

  def _update(self, u):
    if u.tag in self._workers:
      self._update_worker(u)
    else:
      self._add_worker(u)

  def _add_gas_worker(self, u):
    self._workers[u.tag] = (u, WorkerState.GAS)
    self._update_state_by_tag(u.tag, WorkerState.GAS)

  def _update_gas_worker(self, u):
    old_unit = self._workers[u.tag]
    if old_unit[1] == WorkerState.GAS:
      self._workers[u.tag] = (u, WorkerState.GAS)
    else:
      self._remove_state_by_tag(u.tag, old_unit[1])
      self._update_state_by_tag(u.tag, WorkerState.GAS)
      self._workers[u.tag] = (u, WorkerState.GAS)

  def _update_gas_worker(self, u):

  def _add_worker(self, u):
    state = self._judge_worker_status(u) 
    self._workers[u.tag] = (u, state)
    self._update_state_by_tag(u.tag, state)

  def _update_worker(self, u):
    state = self._judge_worker_status(u) 
    old_unit = self._workers[u.tag]
    if old_unit[1] == state:
      self._workers[u.tag] = (u, state)
    else:
      self._remove_state_by_tag(u.tag, old_unit[1])
      self._update_state_by_tag(u.tag, state)
      self._workers[u.tag] = (u, state)

  def _remove_worker(self, u):
    state = self._judge_worker_status(u)
    self._remove_state_by_tag(u.tag, state)
    self._workers.pop(u.tag)

  def _judge_worker_status(self, u):
    pass


  def _update_state_by_tag(self, tag, state):
    if state == WorkerState.IDLE:
      self._worker_idle.add(u.tag)
    elif state == WorkerState.MINERALS:
      self._worker_minieral.add(u.tag)
    elif state == WorkerState.GAS:
      self._worker_gas.add(u.tag)
    elif state == WorkerState.BUILD:
      self._worker_build.add(u.tag)
    else:
      self._worker_tmpjob.add(u.tag)

  def _remove_state_by_tag(self, tag, state):
    if state == WorkerState.IDLE:
      self._worker_idle.remove(u.tag)
    elif state == WorkerState.MINERALS:
      self._worker_minieral.remove(u.tag)
    elif state == WorkerState.GAS:
      self._worker_gas.remove(u.tag)
    elif state == WorkerState.BUILD:
      self._worker_build.remove(u.tag)
    else:
      self._worker_tmpjob.remove(u.tag)

  def _check_worker(self, u):
    if u.unit_type in WORKER_LIST and \
      u.int_attr.alliance == ALLIANCE_SELF:
      return True
    else:
      return False


