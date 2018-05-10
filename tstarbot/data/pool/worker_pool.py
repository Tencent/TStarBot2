from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm

from enum import Enum, unique

class EmployStatus(Enum):
    EMPLOY_IDLE = 0
    EMPLOY_PRODUCT = 1
    EMPLOY_COMBAT = 2
    EMPLOY_SCOUT = 3

class Worker(object):
    def __init__(self, unit, state):
        self._unit = unit
        self._state = state
        self._employ_status = EmployStatus.EMPLOY_PRODUCT

    @property
    def state(self):
        return self._state

    @property
    def employ_status(self):
        return self._employ_status

    def employ(self, status):
        self._employ_status = status

    @property
    def unit(self):
        return self._unit

class WorkerPool(PoolBase):
    def __init__(self):
        super(WorkerPool, self).__init__()
        self.workers = {}  # dict, {tag: Worker,... }
        
        self.worker_idle_set = set([])  # set, {tag_1, tag_2, ...}
        self.worker_minieral_set = set([])
        self.worker_gas_set = set([])
        self.worker_build_set = set([])
        self.worker_tmpjob_set = set([])

    def employ_worker(self, employ_status):
        idles = self._get_employ_workers(EmployStatus.EMPLOY_IDLE)
        if len(idles) > 0:
            idles[0].employ(employ_status)
            return idles[0]

        if employ_status == EmployStatus.EMPLOY_PRODUCT:
            return None

        products = self._get_employ_workers(EmployStatus.EMPLOY_PRODUCT)
        if len(products) > 0:
            products[0].employ(employ_status)
            return products[0]

        return None

    def release_worker(self, worker):
        if worker.employ_status != EmployStatus.EMPLOY_IDLE:
            worker.employ(EmployStatus.EMPLOY_IDLE)

    def get_employ_workers(self, employ_status):
        return self._get_employ_workers(employ_status)

    def assign_gas(self, u):
        if u.tag in self.workers:
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

        union_tags = set(self.workers.keys())
        del_units = union_tags.difference(new_tags)
        for u in del_units:
            self._remove_worker(u)

    def find_nearest_by_pos(self, x, y):
        least_distance = 0.0
        least_worker = None
        for worker in self.workers.values():
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
            worker = self.workers[tag]
            distance = self._calculate_distances(x, y,
                    worker.unit.float_attr.pos_x, worker.unit.float_attr.pos_y)
            if distance < least_distance:
                least_distance = distance
                least_worker = worker
        return worker

    def get_by_tag(self, tag):
        if tag in self.workers:
            return self.workers[tag]
        else:
            return None

    def get_workers_by_state(self, state):
        return self._get_workerset_by_state(state)

    @property
    def idles(self):
        return self.worker_idle_set

    @property
    def minierals(self):
        return self.worker_minieral_set

    @property
    def gas(self):
        return self.worker_gas_set

    @property
    def builds(self):
        return self.worker_build_set

    def _update(self, u):
        if u.tag in self.workers:
            self._update_worker(u)
        else:
            self._add_worker(u)

    def _add_gas_worker(self, u):
        self.workers[u.tag] = Worker(u, tm.WorkerState.GAS)
        self._update_state_by_tag(u.tag, tm.WorkerState.GAS)

    def _update_gas_worker(self, u):
        old_worker = self.workers[u.tag]
        if old_worker.state == tm.WorkerState.GAS:
            self.workers[u.tag] = Worker(u, tm.WorkerState.GAS)
        else:
            self._remove_state_by_tag(u.tag, old_worker.state)
            self._update_state_by_tag(u.tag, tm.WorkerState.GAS)
            self.workers[u.tag] = Worker(u, tm.WorkerState.GAS)

    def _add_worker(self, u):
        state = self._judge_worker_status(u)
        self.workers[u.tag] = Worker(u, state)
        self._update_state_by_tag(u.tag, state)

    def _update_worker(self, u):
        state = self._judge_worker_status(u)
        old_worker = self.workers[u.tag]
        if old_worker.state == state:
            self.workers[u.tag] = Worker(u, state)
        else:
            self._remove_state_by_tag(u.tag, old_worker.state)
            self._update_state_by_tag(u.tag, state)
            self.workers[u.tag] = Worker(u, state)

    def _remove_worker(self, tag):
        worker = self.workers[tag]
        self._remove_state_by_tag(worker.unit.tag, worker.state)
        self.workers.pop(worker.unit.tag)

    def _judge_worker_status(self, u):
        return self._analysis_orders(u)

    def _analysis_orders(self, u):
        if 0 == len(u.orders):
            return tm.WorkerState.IDLE

        order = u.orders[0]
        #print('order=', order.ability_id)
        if order.ability_id in tm.WORKER_RESOURCE_ABILITY:
            if u.tag in self.worker_gas_set:
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
            self.worker_idle_set.add(tag)
        elif state == tm.WorkerState.MINERALS:
            self.worker_minieral_set.add(tag)
        elif state == tm.WorkerState.GAS:
            self.worker_gas_set.add(tag)
        elif state == tm.WorkerState.BUILD:
            self.worker_build_set.add(tag)
        else:
            self.worker_tmpjob_set.add(tag)

    def _remove_state_by_tag(self, tag, state):
        if state == tm.WorkerState.IDLE:
            self.worker_idle_set.remove(tag)
        elif state == tm.WorkerState.MINERALS:
            self.worker_minieral_set.remove(tag)
        elif state == tm.WorkerState.GAS:
            self.worker_gas_set.remove(tag)
        elif state == tm.WorkerState.BUILD:
            self.worker_build_set.remove(tag)
        else:
            self.worker_tmpjob_set.remove(tag)

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
            return self.worker_idle_set
        elif state == tm.WorkerState.MINERALS:
            return self.worker_minieral_set
        elif state == tm.WorkerState.GAS:
            return self.worker_gas_set
        elif state == tm.WorkerState.BUILD:
            return self.worker_gas_set
        else:
            ids = set([])
            for worker in self.workers.values():
                if worker.state == state:
                    ids.add(worker.unit.tag)
            return ids

    def _get_employ_workers(self, employ_status):
        candidates = []
        for worker in self.workers.values():
                if worker.employ_status == employ_status:
                    candidates.append(worker)
        return candidates


if __name__ == '__main__':
    pool = WorkerPool()
    for i in range(10):
        pool.workers[i] = Worker(i, 0)

    employs = []
    for i in range(15):
        worker = pool.employ_worker(EmployStatus.EMPLOY_SCOUT)
        if worker is None:
            print('employ worker failed, num=', i)
        else:
            print('employ worker, num=', i)
            employs.append(worker)

    scouts = pool.get_employ_workers(EmployStatus.EMPLOY_SCOUT)
    idles = pool.get_employ_workers(EmployStatus.EMPLOY_IDLE)
    products = pool.get_employ_workers(EmployStatus.EMPLOY_PRODUCT)
    combats = pool.get_employ_workers(EmployStatus.EMPLOY_COMBAT)
    print('scouts_num={}, idles_num={}, products_num={}, combats_num={}'.format(
          len(scouts), len(idles), len(products), len(combats)))

    for e in employs:
        pool.release_worker(e)

    scouts = pool.get_employ_workers(EmployStatus.EMPLOY_SCOUT)
    idles = pool.get_employ_workers(EmployStatus.EMPLOY_IDLE)
    products = pool.get_employ_workers(EmployStatus.EMPLOY_PRODUCT)
    combats = pool.get_employ_workers(EmployStatus.EMPLOY_COMBAT)
    print('scouts_num={}, idles_num={}, products_num={}, combats_num={}'.format(
          len(scouts), len(idles), len(products), len(combats)))



