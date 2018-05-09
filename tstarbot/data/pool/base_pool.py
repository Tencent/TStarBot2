from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm
from pysc2.lib.typeenums import UNIT_TYPEID
import copy
import numpy as np

BASE_RANGE = 10.0
BASE_RESOURCE_RANGE = 10.0
BASE_RESOURCE_DISTANCE = 10.0
RESOURCE_DISTANCE = 7.0
BASE_MINERAL_NUM = 8
BASE_GAS_NUM = 2


class ResourceArea(object):
    """ Pure Resource Area, including minerals & gases and excluding bases """

    def __init__(self, pool):
        self._pool = pool
        self.owner_base_tag = None
        self.ideal_base_pos = None
        self.m_pos = []
        self.g_pos = []

    def is_unit_in_area(self, pos_x, pos_y):
        diff_x = abs(pos_x - self.ideal_base_pos[0])
        diff_y = abs(pos_y - self.ideal_base_pos[1])
        return (diff_x < BASE_RESOURCE_DISTANCE and
                diff_y < BASE_RESOURCE_DISTANCE)

    def get_mineral_tags(self):
        mtags = []
        for m in self._pool.minerals.values():
            if self.is_unit_in_area(m.float_attr.pos_x, m.float_attr.pos_y):
                mtags.append(m.tag)
        return mtags

    def get_gas_tags(self):
        gtags = []
        for g in self._pool.vespenes.values():
            if self.is_unit_in_area(g.float_attr.pos_x, g.float_attr.pos_y):
                gtags.append(g.tag)
        return gtags

    def calculate_avg(self):
        num = 0
        sum_x = 0
        sum_y = 0
        for m in self._pool.minerals.values():
            if self.is_unit_in_area(m.float_attr.pos_x, m.float_attr.pos_y):
                sum_x += m.float_attr.pos_x
                sum_y += m.float_attr.pos_y
                num += 1

        for g in self._pool.vespenes.values():
            if self.is_unit_in_area(g.float_attr.pos_x, g.float_attr.pos_y):
                sum_x += g.float_attr.pos_x
                sum_y += g.float_attr.pos_y
                num += 1

        return (sum_x / num, sum_y / num)



class BaseInstance(object):
    """ Base with other items in its territory.
     used by BasePool """

    def __init__(self, unit, pool, resource_area):
        self._tag = unit.tag
        self._unit = unit
        self._pool = pool
        self._resource_area = resource_area

        # unit tag set
        self.mineral_set = set([])  # resource_area.get_mineral_tags())
        self.gas_set = set([])  # resource_area.get_gas_tags())
        self.worker_set = set([])
        self.larva_set = set([])
        self.egg_set = set([])
        self.queen_set = set([])
        self.vb_set = set([])

        self.mineral_remain = 0
        self.mineral_cap = 0
        self.mineral_worker_num = 0
        self.gas_remain = 0
        self.gas_cap = 0
        self.gas_worker_num = 0
        self.gas_building = 0

    @property
    def unit(self):
        return self._unit

    @property
    def resource_area(self):
        return self._resource_area

    def is_unit_in_base(self, unit):
        base_x = self._unit.float_attr.pos_x
        base_y = self._unit.float_attr.pos_y
        u_x = unit.float_attr.pos_x
        u_y = unit.float_attr.pos_y
        dist = self._pool.calculate_distances(base_x, base_y, u_x, u_y)
        if dist < BASE_RANGE:
            return True
        else:
            return False

    def update_unit(self, unit):
        self._unit = unit

    def update_resource(self):
        self.mineral_set = set(self._resource_area.get_mineral_tags())
        self.gas_set = set(self._resource_area.get_gas_tags())


class BasePool(PoolBase):
    def __init__(self, dd):
        super(PoolBase, self).__init__()
        self._dd = dd
        self._init = False

        self._bases = {}  # {base_tag: BaseInstance, ...}
        self._unit_to_base = {}  # map unit to base
        self.resource_cluster = []  # [ResourceArea, ResourceArea, ...]
        self.minerals = {}  # {mineral_tag: unit, ...}
        self.vespenes = {}  # {vespene_tag: unit, ...}
        self.vbs = {}  # {vespene_building_tag: unit, ...}
        self.queens = {}
        self.eggs = {}
        self.larvas = {}

    @property
    def bases(self):
        return self._bases

    def reset(self):
        # print('base_pool reset')
        self._dc = None
        self._init = False
        self._bases = {}
        self._unit_to_base = {}
        self.resource_cluster = []
        self.minerals = {}
        self.vespenes = {}
        self.vbs = {}
        self.queens = {}
        self.eggs = {}
        self.larvas = {}

    def update(self, timestep):
        units = timestep.observation['units']
        if not self._init:
            # self._analysis_resource(units)
            self._init_base(units)
            self._init = True
        else:
            self._update_base(units)

    def find_base_belong(self, unit):
        target_base = None
        mini_dist = None
        # print('base number=', len(self._bases))
        for base in self._bases.values():
            dist = self.calculate_distances(unit.float_attr.pos_x,
                                             unit.float_attr.pos_y,
                                             base.unit.float_attr.pos_x,
                                             base.unit.float_attr.pos_y)
            # print('dist=', dist, ';range=', BASE_RANGE)
            if mini_dist is None:
                mini_dist = dist
                target_base = base
            elif mini_dist > dist:
                mini_dist = dist
                target_base = base
            else:
                pass

        return target_base

    def find_base_owner_cluster(self, base_unit):
        base_x = base_unit.float_attr.pos_x
        base_y = base_unit.float_attr.pos_y
        nearest_cluster = None
        nearest_distance = None
        for cluster in self.resource_cluster:
            pos = cluster.ideal_base_pos
            tmp_distance = self.calculate_distances(base_x, base_y, pos[0],
                                                     pos[1])
            if nearest_distance is None or tmp_distance < nearest_distance:
                nearest_distance = tmp_distance
                nearest_cluster = cluster

        # print('base=', (base_x, base_y), 'cluster=', nearest_cluster)
        return nearest_cluster

    def unit_dist(self, unit1, unit2):
        return self.calculate_distances(unit1.float_attr.pos_x,
                                        unit1.float_attr.pos_y,
                                        unit2.float_attr.pos_x,
                                        unit2.float_attr.pos_y)

    def min_dist(self, unit, mtags, gtags, all_minerals, all_gas):
        # minimal dist from unit to mtags and gtags
        d = [self.unit_dist(unit, all_minerals[tag]) for tag in mtags] + \
            [self.unit_dist(unit, all_gas[tag]) for tag in gtags]
        return min(d)

    def find_resource_area(self, mtags, gtags, all_minerals, all_gas):
        area = ResourceArea(self)
        gtags_in_area = []
        tag = mtags.pop()
        mtags_in_area = [tag]
        while mtags:  # not empty
            d_min = None
            mtag = None
            for tag in mtags:
                d = self.min_dist(all_minerals[tag], mtags_in_area,
                                  gtags_in_area, all_minerals, all_gas)
                if d_min is None or d < d_min:
                    d_min = d
                    mtag = tag
            if d_min > RESOURCE_DISTANCE:
                break
            mtags_in_area.append(mtag)
            mtags.discard(mtag)

        while gtags:  # not empty
            d_min = None
            gtag = None
            for tag in gtags:
                d = self.min_dist(all_gas[tag], mtags_in_area,
                                  gtags_in_area, all_minerals, all_gas)
                if d_min is None or d < d_min:
                    d_min = d
                    gtag = tag
            if d_min > RESOURCE_DISTANCE:
                break
            gtags_in_area.append(gtag)
            gtags.discard(gtag)

        m_pos = [[all_minerals[tag].float_attr.pos_x,
                  all_minerals[tag].float_attr.pos_y] for tag in mtags_in_area]
        g_pos = [[all_gas[tag].float_attr.pos_x,
                  all_gas[tag].float_attr.pos_y] for tag in gtags_in_area]
        area.m_pos = m_pos
        area.g_pos = g_pos
        ideal_pos = self.find_ideal_base_position(np.array(m_pos),
                                                  np.array(g_pos))
        area.ideal_base_pos = ideal_pos
        return area

    def find_ideal_base_position(self, m_pos, g_pos):
        mean_x, mean_y = m_pos.mean(0)
        max_x, max_y = g_pos.min(0) + 10
        min_x, min_y = g_pos.max(0) - 10
        d_min = None
        ideal_pos = []
        x = min_x
        while x <= max_x:
            y = min_y
            while y <= max_y:
                if self.can_build_base(x, y, m_pos):
                    d = self.calculate_distances(x, y, mean_x, mean_y)
                    if d_min is None or d < d_min:
                        ideal_pos = [x, y]
                        d_min = d
                y += 1
            x += 1
        return ideal_pos

    def can_build_base(self, x, y, m_pos):
        for pos in m_pos:
            dx = abs(pos[0] - x)
            dy = abs(pos[1] - y)
            if dx < 6 and dy < 6 and (dx < 5 or dy < 5):
                return False
        return True

    def calculate_distances(self, x1, y1, x2, y2):
        x = abs(x1 - x2)
        y = abs(y1 - y2)
        distance = x ** 2 + y ** 2
        return distance ** 0.5

    def _init_base(self, units):
        # print('base_pool init')
        tmps = self._unit_dispatch(units)
        for unit in tmps[1]:
            self.minerals[unit.tag] = unit

        for unit in tmps[2]:
            self.vespenes[unit.tag] = unit

        mtags = set(self.minerals.keys())
        gtags = set(self.vespenes.keys())
        while len(mtags) > 0 and len(gtags) > 0:
            # print('mtags_num=', len(mtags), ';gtags_num=', len(gtags))
            area = self.find_resource_area(mtags, gtags,
                                           self.minerals, self.vespenes)
            self.resource_cluster.append(area)
        # for cluster in self.resource_cluster:
        #    print('clusters=', str(cluster))

        self._update_base_unit(tmps[0])
        self._update_mineral_unit(tmps[1])
        self._update_vespene_unit(tmps[2])
        self._update_vb_unit(tmps[3])
        self._update_egg_unit(tmps[4])
        self._update_queen_unit(tmps[5])
        self._update_larva_unit(tmps[6])
        self._update_resource_for_base()
        self._update_worker_for_base()

    def _update_base(self, units):
        tmps = self._unit_dispatch(units)
        self._update_mineral_unit(tmps[1])
        self._update_vespene_unit(tmps[2])
        self._update_base_unit(tmps[0])
        self._update_vb_unit(tmps[3])
        self._update_egg_unit(tmps[4])
        self._update_queen_unit(tmps[5])
        self._update_larva_unit(tmps[6])
        self._update_resource_for_base()
        self._update_worker_for_base()

    def _update_base_unit(self, bases):
        bids = set([])
        for base in bases:
            if base.tag not in self._bases:
                area = self.find_base_owner_cluster(base)
                new_base = BaseInstance(base, self, area)
                area.owner_base_tag = base.tag
                self._bases[base.tag] = new_base
            else:
                self._bases[base.tag].update_unit(base)
                self._bases[base.tag].update_resource()
            bids.add(base.tag)

        bids_curr = set(self._bases.keys())
        del_bases = bids_curr.difference(bids)
        for bid in del_bases:
            self._remove_base(bid)

    def _remove_base(self, bid):
        self._bases.pop(bid)
        # print('**** remove base ****,=', len(self._bases))

    def _update_resource_for_base(self):
        for base in self._bases.values():
            base.mineral_remain = 0
            base.gas_remain = 0
            for mtag in base.mineral_set:
                unit = self.minerals[mtag]
                base.mineral_remain += unit.int_attr.mineral_contents

            for gtag in base.gas_set:
                unit = self.vespenes[gtag]
                base.gas_remain += unit.int_attr.vespene_contents

    def _update_worker_for_base(self):
        for base in self._bases.values():
            base.worker_set = set([])
            base.mineral_worker_num = 0
            base.gas_worker_num = 0

        wpool = self._dd.worker_pool
        mineral_tags = wpool.get_workers_by_state(tm.WorkerState.MINERALS)
        gas_tags = wpool.get_workers_by_state(tm.WorkerState.GAS)
        idle_tags = wpool.get_workers_by_state(tm.WorkerState.IDLE)
        for wtag in mineral_tags:
            worker = wpool.get_by_tag(wtag)
            base = self.find_base_belong(worker.unit)
            if base is None:
                continue
                # raise Exception('mineral_worker should be in base')
            base.worker_set.add(wtag)
            base.mineral_worker_num += 1

        for wtag in gas_tags:
            worker = wpool.get_by_tag(wtag)
            base = self.find_base_belong(worker.unit)
            if base is None:
                raise Exception('gas_worker should be in base')
            base.worker_set.add(wtag)
            base.gas_worker_num += 1

        for wtag in idle_tags:
            worker = wpool.get_by_tag(wtag)
            base = self.find_base_belong(worker.unit)
            if base is None:
                continue
            base.worker_set.add(wtag)

    def _update_mineral_unit(self, minerals):
        '''clear current mineral record'''
        self.minerals = {}
        mids = set([])
        for m in minerals:
            self.minerals[m.tag] = m
            '''check tag of mineral in base not changed'''
            if m.tag in self._unit_to_base:
                base_tag = self._unit_to_base[m.tag]
                base = self._bases[base_tag]
                if m.tag not in base.mineral_set:
                    raise Exception('mineral in base should not change')
            mids.add(m.tag)

        mids_curr = set(self.minerals.keys())
        del_mids = mids_curr.difference(mids)
        for mid in del_mids:
            self.minerals.pop(mid)
            self._remove_mineral_from_base(mid)

    def _remove_mineral_from_base(self, tag):
        for base in self._bases.values():
            if tag in base.mineral_set:
                base.mineral_set.remove(tag)

    def _update_vespene_unit(self, vespenes):
        self.vespenes = {}
        vids = set([])
        for v in vespenes:
            self.vespenes[v.tag] = v
            '''check the tag of vespene in base not changed'''
            if v.tag in self._unit_to_base:
                base_tag = self._unit_to_base[v.tag]
                base = self._bases[base_tag]
                if v.tag not in base.gas_set:
                    raise Exception('gas in base should not change')
            vids.add(v.tag)

        vids_curr = set(self.vespenes.keys())
        del_vids = vids_curr.difference(vids)
        for vid in del_vids:
            self.vespenes.pop(vid)
            self._remove_vespene_from_base(vid)

    def _remove_vespene_from_base(self, tag):
        for base in self._bases.values():
            if tag in base.gas_set:
                base.gas_set.remove(tag)

    def _update_vb_unit(self, vbs):
        vbids = set([])
        for vb in vbs:
            if vb.tag not in self.vbs:
                self.vbs[vb.tag] = vb
                self._add_vb_to_base(vb)
            else:
                self.vbs[vb.tag] = vb
            vbids.add(vb.tag)

        vbids_curr = set(self.vbs.keys())
        del_vbids = vbids_curr.difference(vbids)
        for vbid in del_vbids:
            self.vbs.pop(vbid)
            self._remove_vb_from_base(vbid)

    def _add_vb_to_base(self, unit):
        base = self.find_base_belong(unit)
        if base is None:
            return
        base.vb_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_vb_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        if base_tag not in self._bases:
            self._unit_to_base.pop(tag)
            return

        if tag in self._bases[base_tag].vb_set:
            self._bases[base_tag].vb_set.remove(tag)
        self._unit_to_base.pop(tag)

    def _update_queen_unit(self, queens):
        qids = set([])
        for q in queens:
            if q.tag not in self.queens:
                self.queens[q.tag] = q
                self._add_queen_to_base(q)
            else:
                self.queens[q.tag] = q
            qids.add(q.tag)

        qids_curr = set(self.queens.keys())
        del_qids = qids_curr.difference(qids)
        for qid in del_qids:
            self.queens.pop(qid)
            self._remove_queen_from_base(qid)

    def _add_queen_to_base(self, unit):
        base = self.find_base_belong(unit)
        if base is None:
            return
        base.queen_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_queen_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        if base_tag not in self._bases:
            self._unit_to_base.pop(tag)
            return

        if tag in self._bases[base_tag].queen_set:
            self._bases[base_tag].queen_set.remove(tag)
            self._unit_to_base.pop(tag)

    def _update_larva_unit(self, larvas):
        # print('larva update')
        lids = set([])
        for l in larvas:
            if l.tag not in self.larvas:
                # print('add larva:', l.tag)
                self.larvas[l.tag] = l
                self._add_larva_to_base(l)
            else:
                # print('add larva:', l.tag)
                self.larvas[l.tag] = l
            lids.add(l.tag)

        lids_curr = set(self.larvas.keys())
        del_lids = lids_curr.difference(lids)
        for lid in del_lids:
            self.larvas.pop(lid)
            self._remove_larva_from_base(lid)

    def _add_larva_to_base(self, unit):
        base = self.find_base_belong(unit)
        if base is None:
            return
        base.larva_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_larva_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        if base_tag not in self._bases:
            self._unit_to_base.pop(tag)
            return

        if tag in self._bases[base_tag].larva_set:
            self._bases[base_tag].larva_set.remove(tag)
        self._unit_to_base.pop(tag)

    def _update_egg_unit(self, eggs):
        eids = set([])
        for e in eggs:
            if e.tag not in self.eggs:
                self.eggs[e.tag] = e
                self._add_egg_to_base(e)
            else:
                self.eggs[e.tag] = e
            eids.add(e.tag)

        eids_curr = set(self.eggs.keys())
        del_eids = eids_curr.difference(eids)
        for eid in del_eids:
            self.eggs.pop(eid)
            self._remove_egg_from_base(eid)

    def _add_egg_to_base(self, unit):
        base = self.find_base_belong(unit)
        if base is None:
            return
        base.egg_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_egg_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        if base_tag not in self._bases:
            self._unit_to_base.pop(tag)
            return

        if tag in self._bases[base_tag].egg_set:
            self._bases[base_tag].egg_set.remove(tag)
        self._unit_to_base.pop(tag)

    def _avgs(self, tags, all_mineral, all_gas):
        resource_posx = []
        resource_posy = []
        for tag in tags:
            if tag in all_mineral:
                unit = all_mineral[tag]
                resource_posx.append(unit.float_attr.pos_x)
                resource_posy.append(unit.float_attr.pos_y)
            elif tag in all_gas:
                unit = all_gas[tag]
                resource_posx.append(unit.float_attr.pos_x)
                resource_posy.append(unit.float_attr.pos_y)
            else:
                return None

        avg_x = sum(resource_posx) / len(resource_posx)
        avg_y = sum(resource_posy) / len(resource_posy)
        return avg_x, avg_y

    def _unit_dispatch(self, units):
        tmp_utype = []
        tmp_base = []
        tmp_minerals = []
        tmp_vespene = []
        tmp_vb = []
        tmp_egg = []
        tmp_queen = []
        tmp_larva = []
        for u in units:
            tmp_utype.append(u.unit_type)
            if self._check_base(u):
                tmp_base.append(u)
            elif self._check_mineral(u):
                tmp_minerals.append(u)
            elif self._check_vespene(u):
                tmp_vespene.append(u)
            elif self._check_vespene_buildings(u):
                tmp_vb.append(u)
            elif self._check_egg(u):
                tmp_egg.append(u)
            elif self._check_queen(u):
                tmp_queen.append(u)
            elif self._check_larva(u):
                tmp_larva.append(u)
            else:
                pass  # do nothing

        # print('unit_types=', tmp_utype)
        return (tmp_base, tmp_minerals, tmp_vespene,
                tmp_vb, tmp_egg, tmp_queen, tmp_larva)

    def _check_base(self, u):
        if u.unit_type in tm.BASE_UNITS and \
                        u.int_attr.alliance == tm.AllianceType.SELF.value:
            return True
        else:
            return False

    def _check_mineral(self, u):
        if u.unit_type in tm.MINERAL_UNITS:
            return True
        else:
            return False

    def _check_vespene(self, u):
        if u.unit_type in tm.VESPENE_UNITS:
            return True
        else:
            return False

    def _check_vespene_buildings(self, u):
        if u.unit_type in tm.VESPENE_BUILDING_UNITS and \
                        u.int_attr.alliance == tm.AllianceType.SELF.value:
            return True
        else:
            return False

    def _check_egg(self, u):
        if u.unit_type == UNIT_TYPEID.ZERG_EGG.value and \
                        u.int_attr.alliance == tm.AllianceType.SELF.value:
            return True
        else:
            return False

    def _check_queen(self, u):
        if u.unit_type == UNIT_TYPEID.ZERG_QUEEN.value and \
                        u.int_attr.alliance == tm.AllianceType.SELF.value:
            return True
        else:
            return False

    def _check_larva(self, u):
        if u.unit_type == UNIT_TYPEID.ZERG_LARVA.value and \
                        u.int_attr.alliance == tm.AllianceType.SELF.value:
            # print('larva: ', (u.tag, u.unit_type, u.int_attr.alliance,
            #      tm.AllianceType.SELF.value))
            return True
        else:
            return False

    def _analysis_resource(self, units):
        tmps = self._unit_dispatch(units)
        bases = tmps[0]
        print('base_number=', len(bases))
        minerals = tmps[1]
        vespenes = tmps[2]
        base_x = bases[0].float_attr.pos_x
        base_y = bases[0].float_attr.pos_y
        mineral_dist = []
        mineral_pos = []
        mineral_of_base = []
        mineral_unit_of_base = []
        for mineral in minerals:
            dist = self.calculate_distances(base_x, base_y,
                                             mineral.float_attr.pos_x,
                                             mineral.float_attr.pos_y)
            mineral_dist.append(dist)
            mineral_pos.append((mineral.tag,
                                 mineral.float_attr.pos_x,
                                 mineral.float_attr.pos_y))

            if dist < BASE_RESOURCE_RANGE:
                mineral_of_base.append((mineral.tag,
                                         mineral.float_attr.pos_x,
                                         mineral.float_attr.pos_y))
                mineral_unit_of_base.append(mineral)

        gas_dist = []
        gas_pos = []
        gas_of_base = []
        gas_unit_of_base = []
        for gas in vespenes:
            dist = self.calculate_distances(base_x, base_y,
                                             gas.float_attr.pos_x,
                                             gas.float_attr.pos_y)
            gas_dist.append(dist)
            gas_pos.append(
                (gas.tag, gas.float_attr.pos_x, gas.float_attr.pos_y))
            if dist < BASE_RESOURCE_RANGE:
                gas_of_base.append(
                    (gas.tag, gas.float_attr.pos_x, gas.float_attr.pos_y))
                gas_unit_of_base.append(gas)

        unit_x = []
        unit_y = []
        diff_x = []
        diff_y = []
        for unit in mineral_unit_of_base:
            diff_x.append(unit.float_attr.pos_x - base_x)
            diff_y.append(unit.float_attr.pos_y - base_y)
            unit_x.append(unit.float_attr.pos_x)
            unit_y.append(unit.float_attr.pos_y)

        for unit in gas_unit_of_base:
            diff_x.append(unit.float_attr.pos_x - base_x)
            diff_y.append(unit.float_attr.pos_y - base_y)
            unit_x.append(unit.float_attr.pos_x)
            unit_y.append(unit.float_attr.pos_y)

        x_avg = sum(unit_x) / len(unit_x)
        y_avg = sum(unit_y) / len(unit_y)

        diff_x.sort()
        diff_y.sort()
        print('base_pos=', (bases[0].tag, base_x, base_y))
        print('mineral_dist=', mineral_dist)
        # print('mineral_pos=', mineral_pos)
        print('gas_dist=', gas_dist)
        # print('gas_pos=', gas_pos)
        print('mineral_in_base:', mineral_of_base)
        print('gas_in_base:', gas_of_base)
        print('diff_x', diff_x)
        print('diff_y', diff_y)
        print('x_avg:', x_avg)
        print('y_avg:', y_avg)
