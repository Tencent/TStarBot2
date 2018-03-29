from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as tm
from pysc2.lib.typeenums import UNIT_TYPEID
import copy

BASE_RANGE = 20.0
BASE_RESOURCE_RANGE = 10.0
BASE_RESOURCE_DISTANCE = 15.0
BASE_MINIERAL_NUM = 8
BASE_GAS_NUM = 2

class BaseInstance(object):
    def __init__(self, unit, pool, resource_area):
        self._tag = unit.tag
        self._unit = unit
        self._pool = pool
        ''' resource area'''
        self._resource_area = resource_area

        self.minieral_set = copy.deepcopy(self._resource_area.mtags)
        self.gas_set = copy.deepcopy(self._resource_area.gtags)
        self.worker_set = set([])
        self.larva_set = set([])
        self.egg_set = set([])
        self.queen_set = set([])
        self.vb_set = set([])

        self.minieral_remain = 0
        self.minieral_cap = 0
        self.minieral_worker_num = 0
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
        dist = self._pool._calculate_distances(base_x, base_y, u_x, u_y)
        if dist < BASE_RANGE:
            return True
        else:
            return False

    def update_unit(self, unit):
        self._unit = unit

class ResourceArea(object):
    def __init__(self, pool):
        self._owner_mtag = set([])
        self._owner_gtag = set([])
        self._pool = pool
        self._owner_base_tag = None

    def is_belong_to_base(self):
        if self._owner_base_tag is None:
            return False
        else:
            return True 

    def owner_base_tag(self):
        return self._owner_base_tag

    def set_owner_base(self, tag):
        self._owner_base_tag = tag

    def is_empty(self):
        if 0 == len(self._owner_mtag) and 0 == len(self._owner_gtag):
            #print('rc is empty')
            return True
        else:
            return False

    @property
    def mtags(self):
        return self._owner_mtag

    @property
    def gtags(self):
        return self._owner_gtag

    def add_mineral_tag(self, mtag):
        self._owner_mtag.add(mtag)

    def add_gas_tag(self, gtag):
        self._owner_gtag.add(gtag)

    def remove_minieral_tag(self, mtag):
        self._owner_mtag.remove(mtag)

    def remove_gas_tag(self, gtag):
        self._owner_gtag.remove(gtag)

    def avg_pos(self):
        resource_posx = []
        resource_posy = []
        for tag in self._owner_mtag:
            unit = self._pool.minierals[tag]
            resource_posx.append(unit.float_attr.pos_x)
            resource_posy.append(unit.float_attr.pos_y)

        for tag in self._owner_gtag:
            unit = self._pool.vespenes[tag]
            resource_posx.append(unit.float_attr.pos_x)
            resource_posy.append(unit.float_attr.pos_y)

        avg_x = sum(resource_posx) / len(resource_posx)
        avg_y = sum(resource_posy) / len(resource_posy)
        return avg_x, avg_y

    def is_unit_in_cluster(self, tag):
        unit = None
        if tag in self._pool.minierals:
            unit = self._pool.minierals[tag]
        elif tag in self._pool.vespenes:
            unit = self._pool.vespenes[tag]
        else:
            return False

        avg_x, avg_y = self.avg_pos()
        diff_x = abs(avg_x - unit.float_attr.pos_x)
        diff_y = abs(avg_y - unit.float_attr.pos_y)
        return diff_x < BASE_RESOURCE_DISTANCE and diff_y < BASE_RESOURCE_DISTANCE

    def __str__(self):
        minineral_pos = []
        for tag in self._owner_mtag:
            unit = self._pool.minierals[tag]
            minineral_pos.append((unit.float_attr.pos_x, unit.float_attr.pos_y))

        gas_pos = []
        for tag in self._owner_gtag:
            unit = self._pool.vespenes[tag]
            gas_pos.append((unit.float_attr.pos_x, unit.float_attr.pos_y))
        return 'minieral:{},gas:{}'.format(minineral_pos, gas_pos)


class BasePool(PoolBase):
    def __init__(self, dd):
        super(PoolBase, self).__init__()
        self._dd = dd
        self._init = False
        """{base_tag: BaseInstance, ...} """
        self._bases = {}
        """ map unit to base """
        self._unit_to_base = {}
        """
        the resource region that has no base in it.
        [ResourceArea, ResourceArea, ...]
        """
        self.resource_cluster = []
        """{minieral_tag: unit, ...} """
        self.minierals = {}
        """{vespene_tag: unit, ...} """
        self.vespenes = {}
        """{vespene_building_tag: unit, ...} """
        self.vbs = {}
        self.queens = {}
        self.eggs = {}
        self.larvas = {}

    @property
    def bases(self):
        return self._bases

    def reset(self):
        print('base_pool reset')
        self._dc = None
        self._init = False
        self._bases = {}
        self._unit_to_base = {}
        self.resource_cluster = []
        self.minierals = {}
        self.vespenes = {}
        self.vbs = {}
        self.queens = {}
        self.eggs = {}
        self.larvas = {}

    def update(self, timestep):
        units = timestep.observation['units']
        if not self._init:
            #self._analysis_resource(units)
            self._init_base(units)
            self._init = True
        else:
            self._update_base(units)

    def _init_base(self, units):
        print('base_pool init')
        empty_base = []
        tmps = self._unit_dispatch(units)
        for unit in tmps[1]:
            self.minierals[unit.tag] = unit

        for unit in tmps[2]:
            self.vespenes[unit.tag] = unit

        mtags = set(self.minierals.keys())
        gtags = set(self.vespenes.keys())
        while len(mtags) > 0 and len(gtags) > 0:
            #print('mtags_num=', len(mtags), ';gtags_num=', len(gtags))
            area = self.find_resource_area(mtags, gtags)
            self.resource_cluster.append(area)

        #for cluster in self.resource_cluster:
        #    print('clusters=', str(cluster))

        self._update_base_unit(tmps[0])
        self._update_minieral_unit(tmps[1])
        self._update_vespene_unit(tmps[2])
        self._update_vb_unit(tmps[3])
        self._update_egg_unit(tmps[4])
        self._update_queen_unit(tmps[5])
        self._update_larva_unit(tmps[6])
        #self._update_resource_for_base()
        #self._update_worker_for_base()
        #self._update_statistic_for_base()

    def _update_base(self, units):
        tmps = self._unit_dispatch(units)
        self._update_base_unit(tmps[0])
        self._update_minieral_unit(tmps[1])
        self._update_vespene_unit(tmps[2])
        self._update_vb_unit(tmps[3])
        self._update_egg_unit(tmps[4])
        self._update_queen_unit(tmps[5])
        self._update_larva_unit(tmps[6])
        #self._update_resource_for_base()
        #self._update_worker_for_base()
        #self._update_statistic_for_base()

    def _update_base_unit(self, bases):
        bids = set([])
        for base in bases:
            if base.tag not in self._bases:
                area = self.find_base_owner_cluster(base)
                new_base = BaseInstance(base, self, area)
                area.set_owner_base(base.tag)
                self._bases[base.tag] = new_base
            else:
                self._bases[base.tag].update_unit(base)
            bids.add(base.tag)

        bids_curr = set(self._bases.keys())
        del_bases = bids_curr.difference(bids)
        for bid in del_bases:
            self._remove_base(bid)

    def _remove_base(self, bid):
        pass

    def _update_resource_for_base(self):
        pass

    def _update_worker_for_base(self):
        wpool = self._dd.worker_pool
        minieral_workers = wpool.get_workers_by_state(tm.WorkerState.MINIERAL_UNITS)
        gas_workers = wpool.get_workers_by_state(tm.WorkerState.GAS)
        idle_workers = wpool.get_workers_by_state(tm.WorkerState.IDLE)
        for mworker in minieral_workers:
            base = None
            wtag = mworker.unit.tag
            base = self.find_base_belong(mworker.unit)
            if base is None:
                raise Exception('minieral_worker should be in base')
            base.worker_set.add(wtag)
            base.minieral_worker_num += 1

        for gworker in gas_workers:
            base = None
            gtag = gworker.unit.tag
            base = self.find_base_belong(gworker.unit)
            if base is None:
                raise Exception('gas_worker should be in base')
            base.worker_set.add(gtag)
            base.gas_worker_num += 1

    def _update_statistic_for_base(self):
        pass

    def _update_minieral_unit(self, minierals):
        mids = set([])
        for m in minierals:
            if m.tag in self.minierals:
                self.minierals[m.tag] = m
            else:
                if self._init:
                    raise Exception('all minierals will be add after init')
                self.minierals[m.tag] = m
            self.minierals[m.tag] = m
            mids.add(m.tag)

        mids_curr = set(self.minierals.keys())
        del_mids = mids_curr.difference(mids)
        for mid in del_mids:
            self.minierals.pop(mid)
            self._remove_minieral_from_base(mid)

    def _remove_minieral_from_base(self, tag):
        pass

    def _update_vespene_unit(self, vespenes):
        vids = set([])
        for v in vespenes:
            if v.tag in self.vespenes:
                '''update vespene'''
                self.vespenes[v.tag] = v
            else:
                if self._init:
                    raise Exception('no gas will be add after init')
                self.vespenes[v.tag] = v
            vids.add(v.tag)

        vids_curr = set(self.vespenes.keys())
        del_vids = vids_curr.difference(vids)
        for vid in del_vids:
            self.vespenes.pop(vid)
            self._remove_vespene_from_base(vid)

    def _remove_vespene_from_base(self, tag):
        pass

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
        base.vb_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_vb_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
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
        base.queen_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_queen_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        self._bases[base_tag].queen_set.remove(tag)
        self._unit_to_base.pop(tag)

    def _update_larva_unit(self, larvas):
        #print('larva update')
        lids = set([])
        for l in larvas:
            if l.tag not in self.larvas:
                #print('add larva:', l.tag)
                self.larvas[l.tag] = l
                self._add_larva_to_base(l)
            else:
                #print('add larva:', l.tag)
                self.larvas[l.tag] = l
            lids.add(l.tag)

        lids_curr = set(self.larvas.keys())
        del_lids = lids_curr.difference(lids)
        for lid in del_lids:
            self.larvas.pop(lid)
            self._remove_larva_from_base(lid)

    def _add_larva_to_base(self, unit):
        base = self.find_base_belong(unit)
        base.larva_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_larva_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
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
        base.egg_set.add(unit.tag)
        self._unit_to_base[unit.tag] = base.unit.tag

    def _remove_egg_from_base(self, tag):
        if tag not in self._unit_to_base:
            # none belong to any base
            return
        base_tag = self._unit_to_base[tag]
        self._bases[base_tag].egg_set.remove(tag)
        self._unit_to_base.pop(tag)

    def find_base_belong(self, unit):
        target_base = None
        #print('base number=', len(self._bases))
        for base in self._bases.values():
            dist = self._calculate_distances(unit.float_attr.pos_x,
                                      unit.float_attr.pos_y,
                                      base.unit.float_attr.pos_x,
                                      base.unit.float_attr.pos_y)
            #print('dist=', dist, ';range=', BASE_RANGE)
            if dist < BASE_RANGE:
                target_base = base
        return target_base

    def find_base_owner_cluster(self, base_unit):
        base_x = base_unit.float_attr.pos_x
        base_y = base_unit.float_attr.pos_y
        nearest_cluster = None
        nearest_distance = 0
        for cluster in self.resource_cluster:
            pos_x, pos_y = cluster.avg_pos()
            tmp_distance = self._calculate_distances(base_x, base_y, pos_x, pos_y)
            if nearest_distance == 0 or tmp_distance < nearest_distance:
                nearest_distance = tmp_distance
                nearest_cluster = cluster

        #print('base=', (base_x, base_y), 'cluster=', nearest_cluster)
        return nearest_cluster

    def find_resource_area(self, mtags, gtags):
        area = ResourceArea(self)
        for tag in mtags:
            if area.is_empty():
                area.add_mineral_tag(tag)
                #print('area_m_num=', len(area.mtags))
            elif area.is_unit_in_cluster(tag):
                area.add_mineral_tag(tag)
                #print('area_m_num=', len(area.mtags))
            else:
                pass

        for tag in gtags:
            if area.is_unit_in_cluster(tag):
               area.add_gas_tag(tag)
               #print('area_m_num=', len(area.gtags))

        for tag in area.mtags:
            mtags.remove(tag)
        for tag in area.gtags:
            gtags.remove(tag)

        return area

    def _unit_dispatch(self, units):
        tmp_utype = []
        tmp_base = []
        tmp_minierals = []
        tmp_vespene = []
        tmp_vb = []
        tmp_egg = []
        tmp_queen = []
        tmp_larva = []
        for u in units:
            tmp_utype.append(u.unit_type)
            if self._check_base(u):
                tmp_base.append(u)
            elif self._check_minieral(u):
                tmp_minierals.append(u)
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
                pass # do nothing

        #print('unit_types=', tmp_utype)
        return (tmp_base, tmp_minierals, tmp_vespene, 
                tmp_vb, tmp_egg, tmp_queen, tmp_larva)


    def _check_base(self, u):
        if u.unit_type in tm.BASE_UNITS and \
            u.int_attr.alliance == tm.AllianceType.SELF.value:
            return True
        else:
            return False

    def _check_minieral(self, u):
        if u.unit_type in tm.MINIERAL_UNITS:
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
            #print('larva: ', (u.tag, u.unit_type, u.int_attr.alliance, tm.AllianceType.SELF.value))
            return True
        else:
            return False

    def _calculate_distances(self, x1, y1, x2, y2):
        x = abs(x1 - x2)
        y = abs(y1 - y2)
        distance = x ** 2 + y ** 2
        return distance ** 0.5

    def _analysis_resource(self, units):
        tmps = self._unit_dispatch(units)
        bases = tmps[0]
        print('base_number=', len(bases))
        minierals = tmps[1]
        vespenes = tmps[2]
        base_x = bases[0].float_attr.pos_x
        base_y = bases[0].float_attr.pos_y
        minieral_dist = []
        minieral_pos = []
        minieral_of_base = []
        minieral_unit_of_base = []
        for minieral in minierals:
            dist = self._calculate_distances(base_x, base_y, 
                                             minieral.float_attr.pos_x, 
                                             minieral.float_attr.pos_y)
            minieral_dist.append(dist)
            minieral_pos.append((minieral.tag, 
                                 minieral.float_attr.pos_x, 
                                 minieral.float_attr.pos_y))

            if dist < BASE_RESOURCE_RANGE:
                minieral_of_base.append((minieral.tag, 
                                        minieral.float_attr.pos_x, 
                                        minieral.float_attr.pos_y))
                minieral_unit_of_base.append(minieral)


        gas_dist = []
        gas_pos = []
        gas_of_base = []
        gas_unit_of_base = []
        for gas in vespenes:
            dist = self._calculate_distances(base_x, base_y,
                                             gas.float_attr.pos_x,
                                             gas.float_attr.pos_y)
            gas_dist.append(dist)
            gas_pos.append((gas.tag, gas.float_attr.pos_x, gas.float_attr.pos_y))
            if dist < BASE_RESOURCE_RANGE:
                gas_of_base.append((gas.tag, gas.float_attr.pos_x, gas.float_attr.pos_y))
                gas_unit_of_base.append(gas)

        unit_x = []
        unit_y = []
        diff_x = []
        diff_y = [] 
        for unit in minieral_unit_of_base:
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
        print('minieral_dist=', minieral_dist)
        #print('minieral_pos=', minieral_pos)
        print('gas_dist=', gas_dist)
        #print('gas_pos=', gas_pos)
        print('minieral_in_base:', minieral_of_base)
        print('gas_in_base:', gas_of_base)
        print('diff_x', diff_x)
        print('diff_y', diff_y)
        print('x_avg:', x_avg)
        print('y_avg:', y_avg)
