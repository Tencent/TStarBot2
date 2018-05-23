from __future__ import print_function
import pysc2.lib.typeenums as tp
import tstarbot.data.pool.opponent_pool as op

OPENING_STAGE = 5000
BANELING_RUSH_THRESHOLD = 20
ROACH_RUSH_THRESHOLD = 4
ZERG_ROACH_RUSH_THRESHOLD = 15
ROACH_SUPPRESS_THRESHOLD = 10

class OppoMonitor(object):
    def __init__(self):
        #{type: number, .....}
        self._scout_max = {}
        self._scout_curr = {}
        self._scout_change = {}
        self._step_count = 0

    def analysis(self, dc):
        self._step_count = dc.sd.obs['game_loop'][0]
        spool = dc.dd.scout_pool
        scouts = spool.get_view_scouts()
        #print("Scount monitor, scouts={},step={}".format(
        #      len(scouts), self._step_count))
        if (self._step_count < OPENING_STAGE and
            dc.dd.oppo_pool.opening_tactics is None):
            self.analysis_opening_tactis(scouts)
            self.judge_opening_tactis(dc)
        elif (self._step_count == OPENING_STAGE and
              dc.dd.oppo_pool.opening_tactics is None):
            print('SCOUT oppo monitor, un-known, step=', self._step_count)
            dc.dd.oppo_pool.opening_tactics = op.OppoOpeningTactics.UNKNOWN
        else:
            pass

    def judge_opening_tactis(self, dc):
        if self.is_roach_rush():
            print('SCOUT oppo monitor, ROACH_RUSH, step=', self._step_count)
            dc.dd.oppo_pool.opening_tactics = op.OppoOpeningTactics.ROACH_RUSH
        elif self.is_baneling_rush():
            print('SCOUT oppo monitor, BANELING_RUSH, step=', self._step_count)
            dc.dd.oppo_pool.opening_tactics = op.OppoOpeningTactics.BANELING_RUSH
        elif self.is_zerg_roach_rush():
            print('SCOUT oppo monitor, ZERG_ROACH_RUSH, step=', self._step_count)
            dc.dd.oppo_pool.opening_tactics = op.OppoOpeningTactics.ZERGROACH_RUSH
        elif self.is_roach_suppress():
            print('SCOUT oppo monitor, ROACH_SUPPRESS, step=', self._step_count)
            dc.dd.oppo_pool.opening_tactics = op.OppoOpeningTactics.ROACH_SUPPRESS
        else:
            pass

    def analysis_opening_tactis(self, scouts):
        self._scout_curr = {}
        self._scout_change = {}
        for scout in scouts:
            for unit in scout.snapshot_armys:
                if unit.unit_type in self._scout_curr:
                    self._scout_curr[unit.unit_type] += 1
                else:
                    self._scout_curr[unit.unit_type] = 1

        max_keys = set(self._scout_curr.keys())
        curr_keys = set(self._scout_max.keys())

        exist_keys = max_keys.intersection(curr_keys)
        add_keys = max_keys.difference(curr_keys)
        del_keys = curr_keys.difference(max_keys)

        for key in exist_keys:
            v_max = self._scout_max[key]
            v_curr = self._scout_curr[key]
            if v_curr > v_max:
                self._scout_max[key] = v_curr
                self._scout_change[key] = v_curr - v_max

        for key in add_keys:
            self._scout_max[key] = self._scout_curr[key]
            self._scout_change[key] = self._scout_curr[key]

        #print("Scout max={}, curr={}, change={}".format(
        #      self._scout_max, self._scout_curr, self._scout_change))

    def is_baneling_rush(self):
        baneling_t = tp.UNIT_TYPEID.ZERG_BANELING.value
        zergling_t = tp.UNIT_TYPEID.ZERG_ZERGLING.value
        if baneling_t not in self._scout_max or zergling_t not in self._scout_max:
            return False
        max_num = self._scout_max[baneling_t] + self._scout_max[zergling_t]
        if max_num >= BANELING_RUSH_THRESHOLD:
            return True
        else:
            return False

    def is_zerg_roach_rush(self):
        roach_t = tp.UNIT_TYPEID.ZERG_ROACH.value
        zergling_t = tp.UNIT_TYPEID.ZERG_ZERGLING.value
        if roach_t not in self._scout_max or zergling_t not in self._scout_max:
            return False

        max_num = self._scout_max[roach_t] + self._scout_max[zergling_t]
        if max_num >= ZERG_ROACH_RUSH_THRESHOLD:
            return True
        else:
            return False

    def is_roach_rush(self):
        roach_t = tp.UNIT_TYPEID.ZERG_ROACH.value
        if roach_t not in self._scout_max or len(self._scout_max) > 2:
            return False

        max_num = self._scout_max[roach_t]
        if max_num >= ROACH_RUSH_THRESHOLD:
            return True
        else:
            return False

    def is_roach_suppress(self):
        roach_t = tp.UNIT_TYPEID.ZERG_ROACH.value
        ravager_t = tp.UNIT_TYPEID.ZERG_RAVAGER.value
        if roach_t not in self._scout_max or ravager_t not in self._scout_max:
            return False

        max_num = self._scout_max[roach_t] + self._scout_max[ravager_t]
        if max_num >= ROACH_SUPPRESS_THRESHOLD:
            return True
        else:
            return False


