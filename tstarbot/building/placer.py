"""Building Placer"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from math import pi
from math import cos
from math import sin
from math import atan2
from math import sqrt
from random import uniform

from pysc2.lib.typeenums import UNIT_TYPEID


def dist_to_pos(unit, pos):
    return ((unit.float_attr.pos_x - pos[0])**2 +
            (unit.float_attr.pos_y - pos[1])**2)**0.5


def collect_units_by_tags(units, tags):
    uu = []
    for tag in tags:
        u = find_by_tag(units, tag)
        if u:
            uu.append(u)
    return uu


def find_by_tag(units, tag):
    for u in units:
        if u.tag == tag:
            return u
    return None


def list_mean(l):
    if not l:
        return None
    return sum(l) / float(len(l))


def mean_pos(units):
    if not units:
        return ()
    xx = [u.float_attr.pos_x for u in units]
    yy = [u.float_attr.pos_y for u in units]
    return list_mean(xx), list_mean(yy)


def polar_to_cart(rho, theta):
    return rho*cos(theta), rho*sin(theta)


def cart_to_polar(x, y):
    return sqrt(x*x + y*x), atan2(y, x)


class CoordSystem(object):
    def __init__(self, pos_origin, pos_ref):
        self.x_o, self.y_o = pos_origin[0], pos_origin[1]
        x_d, y_d = (pos_origin[0] - pos_ref[0], pos_origin[1] - pos_ref[1])
        self.theta = pi/2 - atan2(y_d, x_d)

    def local_to_global(self, local_xy):
        xdot, ydot = local_xy[0], local_xy[1]
        x = self.x_o + xdot*cos(self.theta) + ydot*sin(self.theta)
        y = self.y_o - xdot*sin(self.theta) + ydot*cos(self.theta)
        return x, y

    def global_to_local(self, global_xy):
        raise NotImplementedError


class BasicPlacer(object):
    def __init__(self):
        self.verbose = 0

    def reset(self):
        pass

    def update(self, dc):
        pass

    def get_planned_pos(self, cmd, dc):
        pass


class NaivePredefPlacer(BasicPlacer):
    """ Naive pre-defined positions """

    def __init__(self):
        super(NaivePredefPlacer, self).__init__()
        self.delta_pos = {
            UNIT_TYPEID.ZERG_SPAWNINGPOOL.value: [6, 0],
            UNIT_TYPEID.ZERG_ROACHWARREN.value: [0, -6],
            UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value: [-3, -8],
            UNIT_TYPEID.ZERG_HYDRALISKDEN.value: [6, -3],
            UNIT_TYPEID.ZERG_SPIRE.value: [3, -6],
            UNIT_TYPEID.ZERG_LURKERDENMP.value: [7, -7],
            UNIT_TYPEID.ZERG_INFESTATIONPIT.value: [1, -9],
            UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value: [7, 7],
            UNIT_TYPEID.ZERG_SPINECRAWLER.value: [-3, -5]
        }

    def reset(self):
        # REMEMBER this!!
        self.delta_pos[UNIT_TYPEID.ZERG_SPINECRAWLER.value] = [-3, -5]

    def update(self, dc):
        pass

    def get_planned_pos(self, cmd, dc):
        if not hasattr(cmd, 'base_tag') or not hasattr(cmd, 'unit_type'):
            return ()

        unit_type = cmd.unit_type
        if unit_type not in self.delta_pos:  # unrecognized building type...
            if self.verbose >= 1:
                print("NaivePredefPlacer: unrecognized building type".format(
                    unit_type))
            return ()

        base_tag = cmd.base_tag
        base_instance = dc.dd.base_pool.bases[base_tag]
        base_x = base_instance.unit.float_attr.pos_x
        base_y = base_instance.unit.float_attr.pos_y
        if base_x < base_y:
            planned_pos = (base_x + self.delta_pos[unit_type][0],
                           base_y + self.delta_pos[unit_type][1])
        else:
            planned_pos = (base_x - self.delta_pos[unit_type][0],
                           base_y - self.delta_pos[unit_type][1])

        # hack the ZERG_SPINECRAWLER position:
        # add an x-axis offset every time when a new one is built
        if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
            self.delta_pos[unit_type][0] -= 2
            if self.verbose >= 1:
                print('spinecrawler pos: {}, {}'.format(
                    self.delta_pos[unit_type][0],
                    self.delta_pos[unit_type][1])
                )

        return planned_pos


class HybridPlacer(BasicPlacer):
    """ Pre-defined adaptive hybrid positions """

    def __init__(self):
        super(HybridPlacer, self).__init__()
        self.predef_delta_pos = {
            UNIT_TYPEID.ZERG_SPAWNINGPOOL.value: [5, 0],
            UNIT_TYPEID.ZERG_ROACHWARREN.value: [0, 5],
            UNIT_TYPEID.ZERG_SPIRE.value: [-2, 4],
            UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value: [5, 4],
            UNIT_TYPEID.ZERG_HYDRALISKDEN.value: [-4.5, 2],
            UNIT_TYPEID.ZERG_INFESTATIONPIT.value: [-7, 3],
            UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value: [8, 1],
        }
        self._base_cs = {}   # {base_tag: cs, ...}
        self._all_units = None

    def reset(self):
        self._base_cs = {}
        self._all_units = None

    def update(self, dc):
        self._all_units = dc.sd.obs['units']
        pass

    def get_planned_pos(self, cmd, dc):
        if not hasattr(cmd, 'base_tag') or not hasattr(cmd, 'unit_type'):
            return ()

        # build coordinate system by lazy evaluation
        base_instance = dc.dd.base_pool.bases[cmd.base_tag]
        base_tag = base_instance.unit.tag
        self._base_cs[base_tag] = (
            self._base_cs.get(base_tag, False) or
            self._make_base_coord_system(base_instance, dc)
        )

        # use predefined position when possible
        unit_type = cmd.unit_type
        if self.verbose >= 2:
            if unit_type == UNIT_TYPEID.ZERG_HYDRALISKDEN.value:
                print('HybridPlacer: tryting to build ZERG_HYDRALISKDEN')
            if unit_type == UNIT_TYPEID.ZERG_INFESTATIONPIT.value:
                print('HybridPlacer: tryting to build ZERG_INFESTATIONPIT')
            if unit_type == UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value:
                print('HybridPlacer: tryting to build ZERG_ULTRALISKCAVERN')
            if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
                print('HybridPlacer: trying to build ZERG_SPINECRAWLER')

        cs = self._base_cs[base_tag]
        if unit_type in self.predef_delta_pos:
            local_xy = self.predef_delta_pos[unit_type]
            return cs.local_to_global(local_xy)

        # for others, find random position
        return self._find_rand_pos(dc, cs)

    def _make_base_coord_system(self, base_instance, dc):
        base_xy = (base_instance.unit.float_attr.pos_x,
                   base_instance.unit.float_attr.pos_y)

        local_minerals = collect_units_by_tags(
            self._all_units, base_instance.mineral_set)
        local_gas = collect_units_by_tags(
            self._all_units, base_instance.gas_set)
        local_res = local_minerals + local_gas
        res_xy = mean_pos(local_res)

        return CoordSystem(pos_origin=base_xy, pos_ref=res_xy)

    def _find_rand_pos(self, dc, cs):
        # find a random position in the rim
        local_xy = self._find_rand_rim_pos(dc, cs)
        xy = cs.local_to_global(local_xy)

        # detect possible overlap/collision and adjust the position slightly
        def is_overlap(unit, pos_xy):
            dist_thres = 1
            d = dist_to_pos(unit=unit, pos=pos_xy)
            return d <= dist_thres

        max_try, n = 8, 0
        while any(is_overlap(u, xy) for u in self._all_units) and n < max_try:
            local_xy = self._find_rand_rim_pos(dc, cs)
            xy = cs.local_to_global(local_xy)
            n += 1
        if self.verbose >= 1 and n >= max_try:
            print("HybridPlacer: "
                  "Fail to find an available random position")
        return xy

    def _find_rand_rim_pos(self, dc, cs):
        r_lo, r_hi = 9.2, 9.7
        a_lo, a_hi = 75, 110
        rho = uniform(r_lo, r_hi)
        theta = uniform(a_lo, a_hi) / 180 * pi
        return polar_to_cart(rho, theta)


def create_placer(name):
    if name.lower() == 'naive_predef':
        return NaivePredefPlacer()
    elif name.lower() == 'hybrid':
        return HybridPlacer()
    else:
        raise ValueError('Unknown building_placer config value {}'.format(name))
