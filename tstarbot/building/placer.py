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

from tstarbot.production.map_tool import bitmap2array


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


def is_overlap(unit, pos_xy, dist_thres=1):
    d = dist_to_pos(unit=unit, pos=pos_xy)
    return d <= dist_thres


def is_on_creep(creep_map, pos_xy, radius):
    x_min, x_max = 0, creep_map.shape[0] - 1
    y_min, y_max = 0, creep_map.shape[1] - 1
    x_center, y_center = pos_xy[0], pos_xy[1]
    x_lo, x_hi = int(x_center - radius), int(x_center + radius)
    y_lo, y_hi = int(y_center - radius), int(y_center + radius)
    xy = [(x, y) for x in range(x_lo, x_hi+1) for y in range(y_lo, y_hi+1)]
    for pos in xy:
        x, y = pos[0], pos[1]
        if x_min <= x <= x_max and y_min <= y <= y_max:
            if creep_map[y][x] < 1:
                return False
    return True


class PredefBuildingDeltaPos(object):
    """ Pre-defined delta position
    TODO: abstract a common class for all delta position management """

    def __init__(self):
        self._predef_delta_pos = {
            UNIT_TYPEID.ZERG_SPAWNINGPOOL.value: [5, 0],
            UNIT_TYPEID.ZERG_ROACHWARREN.value: [0, 5],
            UNIT_TYPEID.ZERG_SPIRE.value: [-2, 4],
            UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value: [5, 4],
            UNIT_TYPEID.ZERG_HYDRALISKDEN.value: [-4.5, 2],
            UNIT_TYPEID.ZERG_INFESTATIONPIT.value: [-7, 3],
            UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value: [8, 1]
        }
        pass

    def reset(self):
        # TODO: fix this dirty work-around for multiple buildings
        self._predef_delta_pos[UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value] = [5, 4]

    def get_delta_pos(self, unit_type):
        if unit_type not in self._predef_delta_pos:
            return ()
        local_xy = self._predef_delta_pos[unit_type]
        # TODO: fix this dirty work-around for multiple buildings
        if unit_type == UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value:
            self._predef_delta_pos[unit_type] = [3, 7]
        return local_xy


class PredefTowerDeltaPos(object):
    """ TODO: abstract a common class for all delta position management """
    def __init__(self):
        self.predef_delta_pos = [
            [0, 9],
            [-1.5, 8],
            [1.5, 8]
        ]
        self.next_cnt = 0
        pass

    def reset(self):
        self.next_cnt = 0

    def get_delta_pos(self):
        if self.next_cnt == len(self.predef_delta_pos):
            return ()
        pos = self.predef_delta_pos[self.next_cnt]
        self.next_cnt += 1
        return pos


class PredefTowerDeltaPosRingAccess(object):
    """ TODO: abstract a common class for all delta position management """
    def __init__(self, pp=None):
        if pp is None:
            self.predef_delta_pos = [
                [0, 8.5],
                [-2.5, 6],
                [0, 6],
                [2.5, 8.5],
                [2.5, 6],
                [-2.5, 4.5],
                [0, 4.5],
                [2.5, 4.5],
            ]
            # self.predef_delta_pos = [
            #     [0, 8.5],
            #     [-2.5, 6],
            #     [0, 6],
            #     [2.5, 8.5],
            # ]
            for each in self.predef_delta_pos:
                each[0] += 0.5
        else:
            self.predef_delta_pos = pp
        self.next_cnt = 0
        pass

    def reset(self):
        self.next_cnt = 0

    def get_delta_pos(self):
        if self.next_cnt == len(self.predef_delta_pos):
            self.next_cnt = 0  # ring access
        pos = self.predef_delta_pos[self.next_cnt]
        self.next_cnt += 1
        return pos


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


class CoordSystemAnchor(object):
    def __init__(self, pos_origin, pos_ref, local_anchor=(0, 0)):
        self.x_o, self.y_o = pos_origin[0], pos_origin[1]
        x_d, y_d = (pos_origin[0] - pos_ref[0], pos_origin[1] - pos_ref[1])
        self.theta = pi/2 - atan2(y_d, x_d)
        self.local_anchor = local_anchor

    def local_to_global(self, local_xy):
        xdot, ydot = self.local_anchor[0], self.local_anchor[1]
        x = self.x_o + xdot*cos(self.theta) + ydot*sin(self.theta)
        y = self.y_o - xdot*sin(self.theta) + ydot*cos(self.theta)
        dx = local_xy[0] - self.local_anchor[0]
        dy = local_xy[1] - self.local_anchor[1]
        return x + dx, y + dy

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
        self.predef_delta_pos[UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value] = [5, 4]

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
                print('HybridPlacer: trying to build ZERG_HYDRALISKDEN')
            if unit_type == UNIT_TYPEID.ZERG_INFESTATIONPIT.value:
                print('HybridPlacer: trying to build ZERG_INFESTATIONPIT')
            if unit_type == UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value:
                print('HybridPlacer: trying to build ZERG_ULTRALISKCAVERN')
            if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
                print('HybridPlacer: trying to build ZERG_SPINECRAWLER')

        cs = self._base_cs[base_tag]
        if unit_type in self.predef_delta_pos:
            local_xy = self.predef_delta_pos[unit_type]
            if unit_type == UNIT_TYPEID.ZERG_EVOLUTIONCHAMBER.value:
                self.predef_delta_pos[unit_type] = [3, 7]
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


class HybridPlacerV2(BasicPlacer):
    """ Pre-defined adaptive hybrid positions, v2

    based on v1, use a separate sub function for tower placement """

    def __init__(self):
        super(HybridPlacerV2, self).__init__()
        self._building_delta = PredefBuildingDeltaPos()
        self._base_tower_delta = {} # {base_tag: PredefTowerDeltaPos(), ...}
        self._base_cs = {}   # {base_tag: cs, ...}
        self._all_units = None
        self._raw_creep = None
        self._creep_map = None

    def reset(self):
        self._base_cs = {}
        self._all_units = None
        self._raw_creep = None
        self._creep_map = None
        self._building_delta.reset()
        self._base_tower_delta = {}

    def update(self, dc):
        self._all_units = dc.sd.obs['units']
        self._raw_creep = dc.sd.obs['raw_data'].map_state.creep
        self._creep_map = bitmap2array(self._raw_creep).transpose()
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
        cs = self._base_cs[base_tag]
        # build tower placer for each base by lazy evaluation
        self._base_tower_delta[base_tag] = (
            self._base_tower_delta.get(base_tag, False) or
            PredefTowerDeltaPos()
        )

        # use predefined position when possible
        unit_type = cmd.unit_type
        if self.verbose >= 2:
            if unit_type == UNIT_TYPEID.ZERG_HYDRALISKDEN.value:
                print('HybridPlacerV2: trying to build ZERG_HYDRALISKDEN')
            if unit_type == UNIT_TYPEID.ZERG_INFESTATIONPIT.value:
                print('HybridPlacerV2: trying to build ZERG_INFESTATIONPIT')
            if unit_type == UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value:
                print('HybridPlacerV2: trying to build ZERG_ULTRALISKCAVERN')
            if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
                print('HybridPlacerV2: trying to build ZERG_SPINECRAWLER')

        pos = self._can_use_pos_predef(dc, cs, unit_type)
        if pos:
            return pos

        pos = self._can_use_pos_for_towers(dc, cs, base_tag, unit_type)
        if pos:
            return pos

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

    def _can_use_pos_predef(self, dc, cs, unit_type):
        local_xy = self._building_delta.get_delta_pos(unit_type)
        if local_xy:
            return cs.local_to_global(local_xy)
        else:
            return ()

    def _can_use_pos_for_towers(self, dc, cs, base_tag, unit_type):
        if unit_type is not UNIT_TYPEID.ZERG_SPINECRAWLER.value:
            return ()
        local_xy = self._base_tower_delta[base_tag].get_delta_pos()
        if not local_xy:
            return ()
        xy = cs.local_to_global(local_xy)
        r = 1  # TODO: tower's true radius?

        def _is_available_pos(pos_xy):
            return (is_on_creep(self._creep_map, pos_xy, radius=r) and
                    not any(is_overlap(u, pos_xy) for u in self._all_units))

        n_try, max_try = 0, 5
        while not _is_available_pos(xy) and n_try < max_try:
            xy = (xy[0], xy[1] - r)
            n_try += 1
        if self.verbose >= 1 and n_try >= max_try:
            print("HybridPlacerV2: Fail to find an available position for the"
                  " Tower after trying {} times".format(max_try))
        return xy

    def _find_rand_pos(self, dc, cs):
        # find a random position in the rim
        local_xy = self._find_rand_rim_pos(dc, cs)
        xy = cs.local_to_global(local_xy)

        # detect possible overlap/collision and adjust the position slightly
        max_try, n = 8, 0
        while (any(is_overlap(u, xy, dist_thres=2) for u in self._all_units)
               and n < max_try):
            local_xy = self._find_rand_rim_pos(dc, cs)
            xy = cs.local_to_global(local_xy)
            n += 1
        if self.verbose >= 1 and n >= max_try:
            print("HybridPlacerV2: Fail to find an available random position"
                  "after trying {} times".format(max_try))
        return xy

    def _find_rand_rim_pos(self, dc, cs):
        r_lo, r_hi = 6.5, 10.5
        a_lo, a_hi = 60, 120
        rho = uniform(r_lo, r_hi)
        theta = uniform(a_lo, a_hi) / 180 * pi
        return polar_to_cart(rho, theta)


class HybridPlacerV3(HybridPlacerV2):
    """ Pre-defined adaptive hybrid positions, v3

    based on v2, more refined trials when placing towers """

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
        cs = self._base_cs[base_tag]
        # build tower placer for each base by lazy evaluation
        self._base_tower_delta[base_tag] = (
            self._base_tower_delta.get(base_tag, False) or
            PredefTowerDeltaPosRingAccess()
        )

        # use predefined position when possible
        unit_type = cmd.unit_type
        if self.verbose >= 2:
            tmpl = "HybridPlacerV3: trying to build {}"
            if unit_type == UNIT_TYPEID.ZERG_HYDRALISKDEN.value:
                print(tmpl.format('ZERG_HYDRALISKDEN'))
            if unit_type == UNIT_TYPEID.ZERG_INFESTATIONPIT.value:
                print(tmpl.format('ZERG_INFESTATIONPIT'))
            if unit_type == UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value:
                print(tmpl.format('ZERG_ULTRALISKCAVERN'))
            if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
                print(tmpl.format('ZERG_SPINECRAWLER'))

        pos = self._can_use_pos_predef(dc, cs, unit_type)
        if pos:
            return pos

        pos = self._can_use_pos_for_towers(dc, cs, base_tag, unit_type)
        if pos:
            return pos

        return self._find_rand_pos(dc, cs)

    def _can_use_pos_for_towers(self, dc, cs, base_tag, unit_type):
        if unit_type is not UNIT_TYPEID.ZERG_SPINECRAWLER.value:
            return ()

        n_try = 0
        max_try = len(self._base_tower_delta[base_tag].predef_delta_pos)
        r = 2  # intentionally a small radius for later overlap detection

        def _is_available_pos(pos_xy):
            return (is_on_creep(self._creep_map, pos_xy, radius=1) and
                    not any(is_overlap(u, pos_xy) for u in self._all_units))

        def _find_farthest_pos_to_origin(init_local_xy):
            max_try_reduce = 5
            cur_local_xy = init_local_xy
            for _ in range(0, max_try_reduce):
                cur_xy = cs.local_to_global(cur_local_xy)
                if _is_available_pos(cur_xy):
                    return cur_local_xy
                # else: try to make it closer to the origin
                cur_local_xy = (cur_local_xy[0], cur_local_xy[1] - r)
            return ()

        while True:
            if n_try >= max_try:
                break
            local_xy = self._base_tower_delta[base_tag].get_delta_pos()
            assert(local_xy is not None)
            local_xy = _find_farthest_pos_to_origin(local_xy)
            if local_xy:
                # print('local_xy = ', local_xy)
                return cs.local_to_global(local_xy)
            n_try += 1

        if self.verbose >= 1 and n_try >= max_try:
            print("HybridPlacerV3: Fail to find a pre-defined position for the"
                  " Tower after trying {} times".format(max_try))
        return ()


class HybridPlacerV3_1(BasicPlacer):
    """ Pre-defined adaptive hybrid positions, v3_1

    use "anchor point" to calculate local-to-global coord when placing towers,
     which ensures a regular-arranged-tower-grids on anywhere of the global map
    """

    def __init__(self):
        super(HybridPlacerV3_1, self).__init__()
        self._building_delta = PredefBuildingDeltaPos()
        self._base_tower_delta = {} # {base_tag: PredefTowerDeltaPos(), ...}
        self._base_cs = {}   # {base_tag: cs, ...}
        self._base_tower_cs = {}  # {base_tag: cs, ...}
        self._all_units = None
        self._raw_creep = None
        self._creep_map = None

    def reset(self):
        self._base_cs = {}
        self._base_tower_cs = {}
        self._all_units = None
        self._raw_creep = None
        self._creep_map = None
        self._building_delta.reset()
        self._base_tower_delta = {}

    def update(self, dc):
        self._all_units = dc.sd.obs['units']
        self._raw_creep = dc.sd.obs['raw_data'].map_state.creep
        self._creep_map = bitmap2array(self._raw_creep).transpose()
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
        cs = self._base_cs[base_tag]
        self._base_tower_cs[base_tag] = (
            self._base_tower_cs.get(base_tag, False) or
            self._make_base_tower_coord_system(base_instance, dc)
        )
        cs_tower = self._base_tower_cs[base_tag]
        # build tower placer for each base by lazy evaluation
        pp = [
            [0, 8],
            [-2, 8],
            [-2, 6],
            [0, 6],
            [2, 6],
            [2, 8],
            [-2, 4],
            [0, 4],
            [2, 4]
        ]
        # pp = [
        #     [0, 8],
        #     [-2, 8],
        #     [-2, 6],
        #     [0, 6],
        # ]
        for each in pp:
            each[1] += 0.5
        self._base_tower_delta[base_tag] = (
            self._base_tower_delta.get(base_tag, False) or
            PredefTowerDeltaPosRingAccess(pp=pp)
        )

        # use predefined position when possible
        unit_type = cmd.unit_type
        if self.verbose >= 2:
            tmpl = "HybridPlacerV3: trying to build {}"
            if unit_type == UNIT_TYPEID.ZERG_HYDRALISKDEN.value:
                print(tmpl.format('ZERG_HYDRALISKDEN'))
            if unit_type == UNIT_TYPEID.ZERG_INFESTATIONPIT.value:
                print(tmpl.format('ZERG_INFESTATIONPIT'))
            if unit_type == UNIT_TYPEID.ZERG_ULTRALISKCAVERN.value:
                print(tmpl.format('ZERG_ULTRALISKCAVERN'))
            if unit_type == UNIT_TYPEID.ZERG_SPINECRAWLER.value:
                print(tmpl.format('ZERG_SPINECRAWLER'))

        pos = self._can_use_pos_predef(dc, cs, unit_type)
        if pos:
            return pos

        pos = self._can_use_pos_for_towers(dc, cs_tower, base_tag, unit_type)
        if pos:
            return pos

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

    def _make_base_tower_coord_system(self, base_instance, dc):
        base_xy = (base_instance.unit.float_attr.pos_x,
                   base_instance.unit.float_attr.pos_y)

        local_minerals = collect_units_by_tags(
            self._all_units, base_instance.mineral_set)
        local_gas = collect_units_by_tags(
            self._all_units, base_instance.gas_set)
        local_res = local_minerals + local_gas
        res_xy = mean_pos(local_res)

        return CoordSystemAnchor(pos_origin=base_xy, pos_ref=res_xy,
                                 local_anchor=(0, 6.5))

    def _can_use_pos_predef(self, dc, cs, unit_type):
        local_xy = self._building_delta.get_delta_pos(unit_type)
        if local_xy:
            return cs.local_to_global(local_xy)
        else:
            return ()

    def _can_use_pos_for_towers(self, dc, cs, base_tag, unit_type):
        if unit_type is not UNIT_TYPEID.ZERG_SPINECRAWLER.value:
            return ()

        n_try = 0
        max_try = len(self._base_tower_delta[base_tag].predef_delta_pos)
        r = 2  # intentionally a small radius for later overlap detection

        def _is_available_pos(pos_xy):
            return (is_on_creep(self._creep_map, pos_xy, radius=1) and
                    not any(is_overlap(u, pos_xy) for u in self._all_units))

        def _sgn(va):
            if va == 0:
                return 0
            return 1.0 if va > 0 else -1.0

        def _find_farthest_pos_to_base(init_xy, base_xy):
            max_try_reduce = 2
            cur_xy = init_xy
            for i in range(0, max_try_reduce):
                if _is_available_pos(cur_xy):
                    return cur_xy
                # else: try to make it closer to the origin
                dx, dy = cur_xy[0] - base_xy[0], cur_xy[1] - base_xy[1]
                ddx, ddy = 2*_sgn(dx), 2*_sgn(dy)
                if i % 2 == 0:
                    cur_xy = (cur_xy[0], cur_xy[1] - ddy)
                else:
                    cur_xy = (cur_xy[0] - ddx, cur_xy[1])
            return ()

        while True:
            if n_try >= max_try:
                break
            local_xy = self._base_tower_delta[base_tag].get_delta_pos()
            assert(local_xy is not None)
            xy = cs.local_to_global(local_xy)
            xy = _find_farthest_pos_to_base(xy, (cs.x_o, cs.y_o))
            if xy:
                # print('xy = ', xy)
                return xy
            n_try += 1

        if self.verbose >= 1 and n_try >= max_try:
            print("HybridPlacerV3: Fail to find a pre-defined position for the"
                  " Tower after trying {} times".format(max_try))
        return ()

    def _find_rand_pos(self, dc, cs):
        # find a random position in the rim
        local_xy = self._find_rand_rim_pos(dc, cs)
        xy = cs.local_to_global(local_xy)

        # detect possible overlap/collision and adjust the position slightly
        max_try, n = 8, 0
        while (any(is_overlap(u, xy, dist_thres=2) for u in self._all_units)
               and n < max_try):
            local_xy = self._find_rand_rim_pos(dc, cs)
            xy = cs.local_to_global(local_xy)
            n += 1
        if self.verbose >= 1 and n >= max_try:
            print("HybridPlacerV3: Fail to find an available random position"
                  "after trying {} times".format(max_try))
        return xy

    def _find_rand_rim_pos(self, dc, cs):
        r_lo, r_hi = 6.5, 10.5
        a_lo, a_hi = 60, 120
        rho = uniform(r_lo, r_hi)
        theta = uniform(a_lo, a_hi) / 180 * pi
        return polar_to_cart(rho, theta)


def create_placer(name):
    if name.lower() == 'naive_predef':
        return NaivePredefPlacer()
    elif name.lower() == 'hybrid':
        return HybridPlacer()
    elif name.lower() == 'hybrid_v2':
        return HybridPlacerV2()
    elif name.lower() == 'hybrid_v3':
        return HybridPlacerV3()
    elif name.lower() == 'hybrid_v3_1':
        return HybridPlacerV3_1()
    else:
        raise ValueError('Unknown building_placer config value {}'.format(name))
