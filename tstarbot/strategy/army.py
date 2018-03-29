"""Army Class."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.strategy.squad import Squad

class Army(object):
    def __init__(self):
        self._squads = set()
        self._unsquaded_units = set()

    def update(self, combat_pool):
        for squad in self._squads:
            squad.update(combat_pool)
        squaded_units = set.union(
            set(), *[squad.units for squad in self._squads])
        self._unsquaded_units = set(u for u in combat_pool.units
                                    if u not in squaded_units)

    def create_squad(self, units):
        for u in units:
            self._unsquaded_units.remove(u)
        squad = Squad(units)
        self._squads.add(squad)
        return squad

    def delete_squad(self, squad):
        self._unsquaded_units.union(squad.units)
        self._squads.remove(squad)

    @property
    def squads(self):
        return self._squads

    @property
    def unsquaded_units(self):
        return self._unsquaded_units

    @property
    def num_units(self):
        return sum([squad.num_units for squad in self._squads])

    @property
    def num_roach_units(self):
        return sum([squad.num_roach_units for squad in self._squads])

    @property
    def num_zerglings_units(self):
        return sum([squad.num_zerglings_units for squad in self._squads])
