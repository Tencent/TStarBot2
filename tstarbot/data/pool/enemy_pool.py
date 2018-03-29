from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm

class EnemyGroup(object):
    def __init__(self):
        self.num_of_total_units = 0
        self.num_of_worker = 0
        self.num_of_enemy = 0

        self._minerals = []
        self._worker_units = []
        self._enemy_units = []
        self._central_point = {}

    def add_mineral(self, mineral_unit):
        self._minerals.append(mineral_unit)
        self._calc_central_point()

    def add_unit(self, u):
        if u.int_attr.unit_type in tm.COMBAT_UNITS:
            self._enemy_units.append(u)
        elif u.int_attr.unit_type in tm.WORKER_UNITS:
            self._worker_units.append(u)

        self._calc_central_point()

    def do_stat(self):
        self.num_of_worker = len(self._worker_units)
        self.num_of_enemy = len(self._enemy_units)
        self.num_of_total_units = self.num_of_worker + self.num_of_enemy

    def get_central_point(self):
        return self._central_point

    def calc_distance(self, u):
        x = self._central_point['pos_x'] - u.float_attr.pos_x
        y = self._central_point['pos_y'] - u.float_attr.pos_y

        return (x*x + y*y) ** 0.5

    def is_in_mineral_group(self, u):
        MAX_MINERAL_DISTANCE = 15
        for m in self._minerals:
            if self._calc_distance(m, u) < MAX_MINERAL_DISTANCE:
                return True

        return False

    def _calc_central_point(self):
        all = self._minerals + self._enemy_units
        total_x = 0.0
        total_y = 0.0
        for u in all:
            total_x += u.float_attr.pos_x
            total_y += u.float_attr.pos_y

        self._central_point = {'pos_x': total_x / len(all),
            'pos_y': total_y / len(all)}

    def _calc_distance(self, u1, u2):
        x = u1.float_attr.pos_x - u2.float_attr.pos_x
        y = u1.float_attr.pos_y - u2.float_attr.pos_y
        return (x*x + y*y) ** 0.5

class EnemyPool(PoolBase):
    def __init__(self):
        super(PoolBase, self).__init__()
        self._enemy_group = []

    def update(self, timestep):
        self._enemy_group.clear()

        # find all mineral
        units = timestep.observation['units']
        for u in units:
            if u.int_attr.unit_type in tm.MINIERAL_UNITS:
                mineral_group = self._find_enemy_group_by_mineral(u)
                if mineral_group == None:
                    new_group = EnemyGroup()
                    new_group.add_mineral(u)
                    self._enemy_group.append(new_group)
                else:
                    mineral_group.add_mineral(u)

        # add enemy units
        for u in units:
            if u.int_attr.alliance == tm.AllianceType.ENEMY.value:
                enemy_group = self._find_enemy_group_by_unit(u)

                if enemy_group == None:
                    print("ERROR: Can not find a base!!")
                    continue

                enemy_group.add_unit(u)

        # do_stat
        for g in self._enemy_group:
            g.do_stat()

    def get_enemy_group(self):
        return self._enemy_group

    def _find_enemy_group_by_mineral(self, mineral_unit):
        for g in self._enemy_group:
            if g.is_in_mineral_group(mineral_unit):
                return g

        return None

    def _find_enemy_group_by_unit(self, army_unit):
        distance = 100000000.0
        group = None

        for g in self._enemy_group:
            d = g.calc_distance(army_unit)
            if d < distance:
                distance = d
                group = g

        return group
