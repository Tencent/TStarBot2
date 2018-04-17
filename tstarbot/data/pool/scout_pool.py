from tstarbot.data.pool.pool_base import PoolBase
from tstarbot.data.pool import macro_def as md
from pysc2.lib.typeenums import UNIT_TYPEID

MAX_AREA_DISTANCE = 12

class Scout(object):
    def __init__(self, unit, team_id = 0):
        self._unit = unit
        self._lost = False # is building lost
        self.is_doing_task = False

    def unit(self):
        return self._unit

    def set_lost(self, lost):
        self._lost = lost

    def is_lost(self):
        return self._lost

    def is_health(self):
        curr_health = self._unit.float_attr.health 
        max_health = self._unit.float_attr.health_max
        return curr_health == max_health

    def update(self, u):
        if u.int_attr.tag == self._unit.int_attr.tag:   # is the same unit
            self._unit = u
            return True

        return False

    def __str__(self):
        u = self._unit
        return "tag {}, type {}, alliance {}".format(u.int_attr.tag,
            u.int_attr.unit_type, u.int_attr.alliance)


class ScoutBaseTarget(object):
    def __init__(self):
        self.enemy_unit = None
        self.has_enemy_base = False
        self.is_main = False
        self.pos = None
        self.has_scout = False
        self.has_army = False

    def __str__(self):
        return 'pos:{} base:{} main_base:{} scout:{} army:{}'.format(
               self.pos, self.has_enemy_base, 
               self.is_main, self.has_scout, self.has_army)

class ScoutPool(PoolBase):
    def __init__(self, dd):
        super(PoolBase, self).__init__()
        self._scouts = {}    # unit_tag -> Scout
        '''{base_tag: ScoutEnemyBase, ....} '''
        self._scout_base_target = []
        self._dd = dd
        self._init = False
        self.home_pos = None

    def reset(self):
        self._scouts = {}
        self._scout_base_target = []
        self._init = False
        self.home_pos = None

    def enemy_bases(self):
        bases = []
        for base in self._scout_base_target:
            if base.has_enemy_base:
                bases.append(base)
        return bases

    def main_enemy_base(self):
        bases = self.enemy_bases()
        if 0 == len(bases):
            return None

        for base in bases:
            if base.is_main:
                return base
        return bases[0]

    def has_enemy_main_base(self):
        for base in self._scout_base_target:
            if base.is_main:
                return True
        return False

    def update(self, timestep):
        if not self._init:
            self._init_home_pos()
            self._init_scout_base_target()
            self._init = True

        units = timestep.observation['units']
        #self._update_scout(units)
        self._update_all_overlord(units)

    def add_scout(self, u):
        tag = u.int_attr.tag

        if tag in self._scouts:
            #print("update overlord {}".format(u))
            self._scouts[tag].update(u)
        else:
            #print("add overlord {}".format(u))
            self._scouts[tag] = Scout(u)

        self._scouts[tag].set_lost(False)

    def remove_scout(self, tag):
        del self._scouts[tag]

    def list_scout(self):
        scouts = []
        for k, b in self._scouts.items():
            scouts.append(b.unit())

        return scouts

    def _update_all_overlord(self, units):
        # set all scouts 'lost' state
        for k, b in self._scouts.items():
            b.set_lost(True)
            #print('scout=', str(b))

        # update scout
        for u in units:
            if u.int_attr.unit_type == UNIT_TYPEID.ZERG_OVERLORD.value \
                and u.int_attr.alliance == md.AllianceType.SELF.value:
                self.add_scout(u)

        # delete lost scouts
        del_keys = []
        for k, b in self._scouts.items():
            if b.is_lost():
                #print('SCOUT overload is over, tag=', b.unit().tag)
                del_keys.append(k)

        for k in del_keys:
            del self._scouts[k]

    def select_scout(self):
        for scout in self._scouts.values():
            if not scout.is_doing_task and scout.is_health():
                return scout
        return None

    def find_furthest_idle_target(self):
        candidates = []
        for target in self._scout_base_target:
            if target.has_enemy_base:
                continue

            if target.has_army:
                continue

            if target.has_scout:
                continue
            candidates.append(target)

        #print('candidate_idle_targe=', len(candidates))
        furthest_dist = 0.0
        furthest_candidate = None
        for candidate in candidates:
            dist = md.calculate_distance(self.home_pos[0], 
                                         self.home_pos[1], 
                                         candidate.pos[0], 
                                         candidate.pos[1])
            if furthest_dist < dist:
                furthest_dist = dist
                furthest_candidate = candidate

        return furthest_candidate

    def _init_home_pos(self):
        bases = self._dd.base_pool.bases
        if len(bases) != 1:
            raise Exception('only one base in the game begin')
        for base in bases.values():
            self.home_pos = (base.unit.float_attr.pos_x,
                             base.unit.float_attr.pos_y)

    def _init_scout_base_target(self):
        areas = self._dd.base_pool.resource_cluster
        if 0 == len(areas):
            raise Exception('resource areas is none')
        for area in areas:
            scout_target = ScoutBaseTarget()
            scout_target.pos = area.fix_avg_pos
            dist = md.calculate_distance(self.home_pos[0], 
                                         self.home_pos[1], 
                                         scout_target.pos[0], 
                                         scout_target.pos[1])
            if dist > MAX_AREA_DISTANCE:
                self._scout_base_target.append(scout_target)
        #print('SCOUT area_number=', len(areas))
        #print('SCOUT target_number=', len(self._scout_base_target))

