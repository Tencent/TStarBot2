from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm

class Worker(object):
    def __init__(self, unit, state, sub_state=None):
        self._unit = unit
        self._state = state
        self._sub = sub_state 

    @property
    def state(self):
        return self._state

    @property
    def sub_state(self):
        return self._sub

    @property
    def unit(self):
        return self._unit

class WorkerPool(PoolBase):
    def __init__(self):
        super(WorkerPool, self).__init__()
        """the format of workers is {uid: Worker,... }"""
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

    def update(self, timestep):
        units = timestep.observation['units']
        new_tags = set([])
        for u in units:
            if self._check_worker(u):
                self._update(u)
            new_tags.add(u.tag)

        union_tags = set(self._workers.keys())
        del_units = union_tags.difference(new_tags)
        for u in del_units:
            self._remove_worker(u)

    def find_nearest_by_pos(self, x, y):
        least_distance = 0.0
        least_worker = None
        for worker in self._workers.values():
            distance = self._calculate_distances(x, y, 
                    worker.unit.float_attr.pos_x, worker.unit.float_attr.pos_y)
            if distance < least_distance:
                least_distance = distance
                least_worker = worker
        return least_worker

    def find_nearest_by_state(self, x, y, state):
        least_distance = 0.0
        least_worker = None
        worker_sets = self._get_workerset_by_state(state)
        for tag in worker_sets:
            worker = self._workers[tag]
            distance = self._calculate_distances(x, y,
                    worker.unit.float_attr.pos_x, worker.unit.float_attr.pos_y)
            if distance < least_distance:
                least_distance = distance
                least_worker = worker
        return worker

    def get_by_tag(self, tag):
        if tag in self._workers:
            return self._workers[tag]
        else:
            return None

    def get_workers_by_state(self, state):
        return self._get_workerset_by_state(state)

    @property
    def idles(self):
        return self._worker_idle

    @property
    def minierals(self):
        return self._worker_minieral

    @property
    def gas(self):
        return self._worker_gas

    @property
    def builds(self):
        return self._worker_build

    def _update(self, u):
        if u.tag in self._workers:
            self._update_worker(u)
        else:
            self._add_worker(u)

    def _add_gas_worker(self, u):
        self._workers[u.tag] = Worker(u, tm.WorkerState.GAS)
        self._update_state_by_tag(u.tag, tm.WorkerState.GAS)

    def _update_gas_worker(self, u):
        old_worker = self._workers[u.tag]
        if old_worker.state == tm.WorkerState.GAS:
            self._workers[u.tag] = Worker(u, tm.WorkerState.GAS)
        else:
            self._remove_state_by_tag(u.tag, old_worker.state)
            self._update_state_by_tag(u.tag, tm.WorkerState.GAS)
            self._workers[u.tag] = Worker(u, tm.WorkerState.GAS)

    def _add_worker(self, u):
        state = self._judge_worker_status(u)
        self._workers[u.tag] = Worker(u, state)
        self._update_state_by_tag(u.tag, state)

    def _update_worker(self, u):
        state = self._judge_worker_status(u)
        old_worker = self._workers[u.tag]
        if old_worker.state == state:
            self._workers[u.tag] = Worker(u, state)
        else:
            self._remove_state_by_tag(u.tag, old_worker.state)
            self._update_state_by_tag(u.tag, state)
            self._workers[u.tag] = Worker(u, state)

    def _remove_worker(self, tag):
        worker = self._workers[tag]
        self._remove_state_by_tag(worker.unit.tag, worker.state)
        self._workers.pop(worker.unit.tag)

    def _judge_worker_status(self, u):
        return self._analysis_orders(u)

    def _analysis_orders(self, u):
        if 0 == len(u.orders):
            return tm.WorkerState.IDLE

        order = u.orders[0]
        #print('order=', order.ability_id)
        if order.ability_id in tm.WORKER_RESOURCE_ABILITY:
            if u.tag in self._worker_gas:
                return tm.WorkerState.GAS 
            else:
                return tm.WorkerState.MINERALS
        elif order in tm.WORKER_BUILD_ABILITY:
            return tm.WorkerState.BUILD
        elif order in tm.WORKER_COMBAT_ABILITY:
            return tm.WorkerState.COMBAT
        elif order in tm.WORKER_MOVE_ABILITY:
            return tm.WorkerState.MOVE
        else:
            return tm.WorkerState.DEFAULT

    def _update_state_by_tag(self, tag, state):
        if state == tm.WorkerState.IDLE:
            self._worker_idle.add(tag)
        elif state == tm.WorkerState.MINERALS:
            self._worker_minieral.add(tag)
        elif state == tm.WorkerState.GAS:
            self._worker_gas.add(tag)
        elif state == tm.WorkerState.BUILD:
            self._worker_build.add(tag)
        else:
            self._worker_tmpjob.add(tag)

    def _remove_state_by_tag(self, tag, state):
        if state == tm.WorkerState.IDLE:
            self._worker_idle.remove(tag)
        elif state == tm.WorkerState.MINERALS:
            self._worker_minieral.remove(tag)
        elif state == tm.WorkerState.GAS:
            self._worker_gas.remove(tag)
        elif state == tm.WorkerState.BUILD:
            self._worker_build.remove(tag)
        else:
            self._worker_tmpjob.remove(tag)

    def _check_worker(self, u):
        if u.unit_type in tm.WORKER_UNITS and \
            u.int_attr.alliance == tm.AllianceType.SELF.value:
            #print('check worker ok, alliance=', u.int_attr.alliance, ',TYPE_SELF=', tm.AllianceType.SELF.value)
            return True
        else:
            return False

    def _calculate_distances(self, x1, y1, x2, y2):
        x = abs(x1 - x2)
        y = abs(y1 - y2)
        distance = x ** 2 + y ** 2
        return distance ** 0.5

    def _get_workerset_by_state(self, state):
        if state == tm.WorkerState.IDLE:
            return self._worker_idle
        elif state == tm.WorkerState.MINERALS:
            return self._worker_minieral
        elif state == tm.WorkerState.GAS:
            return self._worker_gas
        elif state == tm.WorkerState.BUILD:
            return self._worker_gas
        else:
            ids = set([])
            for worker in self._workers:
                if worker.state == state:
                    ids.add(worker.unit.tag)
            return ids

