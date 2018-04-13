"""EnemyPool Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm
from pysc2.lib.typeenums import UNIT_TYPEID


class EnemyCluster(object):

    def __init__(self, units):
        self._units = units

    def __repr__(self):
        return ('EnemyCluster(CombatUnits(%d), WorkerUnits(%d))' %
                (self.num_combat_units, self.num_worker_units))

    @property
    def num_units(self):
        return len(self._units)

    @property
    def num_worker_units(self):
        return len(self.worker_units)

    @property
    def num_combat_units(self):
        return len(self.combat_units)

    @property
    def units(self):
        return self._units

    @property
    def worker_units(self):
        return [u for u in self._units
                if u.int_attr.unit_type in tm.WORKER_UNITS]

    @property
    def combat_units(self):
        return [u for u in self._units
                if u.int_attr.unit_type in tm.COMBAT_UNITS]

    @property
    def centroid(self):
        x = sum(u.float_attr.pos_x for u in self._units) / len(self._units)
        y = sum(u.float_attr.pos_y for u in self._units) / len(self._units)
        return {'x': x, 'y': y}


class EnemyPool(PoolBase):

    def __init__(self):
        super(PoolBase, self).__init__()
        self._enemy_units = list()
        self._enemy_clusters = list()
        self._self_bases = list()

    def update(self, timestep):
        self._enemy_units = list()
        units = timestep.observation['units']
        for u in units:
            if self._is_enemy_unit(u):
                self._enemy_units.append(u)
            else:
                if (u.int_attr.unit_type == UNIT_TYPEID.ZERG_HATCHERY.value or
                    u.int_attr.unit_type == UNIT_TYPEID.ZERG_LAIR.value or
                            u.int_attr.unit_type == UNIT_TYPEID.ZERG_HIVE):
                    self._self_bases.append(u)

        self._enemy_clusters = list()
        for units in self._agglomerative_cluster(self._enemy_units):
            self.enemy_clusters.append(EnemyCluster(units))

    @property
    def units(self):
        return self._enemy_units

    @property
    def num_worker_units(self):
        return sum(cluster.num_worker_units for cluster in self._enemy_clusters)

    @property
    def num_combat_units(self):
        return sum(cluster.num_combat_units for cluster in self._enemy_clusters)

    @property
    def enemy_clusters(self):
        return self._enemy_clusters

    @property
    def weakest_cluster(self):
        if len(self._enemy_clusters) == 0:
            return None
        return min(self._enemy_clusters,
                   key=lambda c: c.num_combat_units if c.num_combat_units >= 3
                                 else float('inf'))

    @property
    def strongest_cluster(self):
        if len(self._enemy_clusters) == 0:
            return None
        return max(self._enemy_clusters, key=lambda c: c.num_combat_units)

    @property
    def closest_cluster(self):
        if len(self._enemy_clusters) == 0 or len(self._self_bases) == 0:
            return None
        my_base_pos = {'x': self._self_bases[0].float_attr.pos_x,
                       'y': self._self_bases[0].float_attr.pos_y}
        return min(self._enemy_clusters, key=lambda c: self._distance(c.centroid, my_base_pos))

    def _is_enemy_unit(self, u):
        if u.int_attr.alliance != tm.AllianceType.ENEMY.value:
            return False
        else:
            return True

    def _agglomerative_cluster(self, units, merge_distance=20, grid_size=8):

        def get_centroid(units):
            x = sum(u.float_attr.pos_x for u in units) / len(units)
            y = sum(u.float_attr.pos_y for u in units) / len(units)
            return (x, y)

        def agglomerative_step(cluster_map):
            merge_threshold = merge_distance ** 2
            min_distance, min_pair = float('inf'), None
            centroids = list(cluster_map.keys())
            for i in range(len(centroids)):
                xi, yi = centroids[i]
                for j in range(i + 1, len(centroids)):
                    xj, yj = centroids[j]
                    distance = (xi - xj) ** 2 + (yi - yj) ** 2
                    if distance < min_distance:
                        min_distance = distance
                        min_pair = (centroids[i], centroids[j])
            if min_pair is not None and min_distance < merge_threshold:
                cluster = cluster_map[min_pair[0]] + cluster_map[min_pair[1]]
                cluster_map.pop(min_pair[0])
                cluster_map.pop(min_pair[1])
                cluster_map[get_centroid(cluster)] = cluster
                return True
            else:
                return False

        def initial_grid_cluster(units):
            grid_map = collections.defaultdict(list)
            for u in units:
                x_grid = u.float_attr.pos_x // grid_size
                y_grid = u.float_attr.pos_y // grid_size
                grid_map[(x_grid, y_grid)].append(u)
            cluster_map = collections.defaultdict(list)
            for cluster in grid_map.values():
                cluster_map[get_centroid(cluster)] = cluster
            return cluster_map

        cluster_map = initial_grid_cluster(units)
        while agglomerative_step(cluster_map): pass
        return list(cluster_map.values())

    def _distance(self, pos_a, pos_b):
        return ((pos_a['x'] - pos_b['x']) ** 2 + \
                (pos_a['y'] - pos_b['y']) ** 2) ** 0.5
