"""EnemyPool Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm
from pysc2.lib.typeenums import UNIT_TYPEID
from tstarbot.data.pool.macro_def import BUILDING_UNITS
import operator
import numpy as np


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

    def __init__(self, dd):
        super(PoolBase, self).__init__()
        self._dd = dd
        self._enemy_units = list()
        self._enemy_clusters = list()
        self._self_bases = list()
        self._is_set_main_base = False
        self._main_base_pos = None

    def update(self, timestep):
        self._enemy_units = list()
        units = timestep.observation['units']
        if not self._is_set_main_base:
            for u in units:
                if u.int_attr.unit_type in [UNIT_TYPEID.ZERG_HATCHERY.value]:
                    self._main_base_pos = {'x': u.float_attr.pos_x,
                                           'y': u.float_attr.pos_y}
                    self._is_set_main_base = True
                    break

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
    def main_base_pos(self):
        return self._main_base_pos

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

        c_targets = [c for c in self._enemy_clusters
                     if (c.num_units > 1 or
                         (c.num_units == 1 and
                          c.units[0].int_attr.unit_type in BUILDING_UNITS))]
        if len(c_targets) == 0:
            return None
        target_c = min(c_targets,
                       key=lambda c: self._distance(c.centroid, self._main_base_pos))
        return target_c

    @property
    def priority_pos(self):
        sorted_x = sorted(self._dd.base_pool.enemy_home_dist.items(), key=operator.itemgetter(1), reverse=True)
        # sorted_x = sorted(self._dd.base_pool.home_dist.items(), key=operator.itemgetter(1))
        sorted_pos_list = [x[0].ideal_base_pos for x in sorted_x]
        for pos in sorted_pos_list:
            pos = {'x': pos[0],
                   'y': pos[1]}
            detected = [u for u in self.units
                        if u.int_attr.unit_type in BUILDING_UNITS and
                        self._distance({'x': u.float_attr.pos_x,
                                        'y': u.float_attr.pos_y}, pos) < 10]
            if len(detected) > 0:
                return pos
        return None

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

    def _cal_dist(self, u1, u2):
        pos_a = {'x': u1.float_attr.pos_x,
                 'y': u1.float_attr.pos_y}
        pos_b = {'x': u2.float_attr.pos_x,
                 'y': u2.float_attr.pos_y}
        return self._distance(pos_a, pos_b)
