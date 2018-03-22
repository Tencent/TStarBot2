"""data context"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tstarbot.data.static_data import StaticData
from tstarbot.data.dynamic_data import DynamicData

class DataContext:
    def __init__(self):
        self._dynamic = DynamicData()
        self._static = StaticData()

    def update(self, timestep):
        # self._obs = timestep.observation
        self._dynamic.update(timestep)
        self._static.update(timestep)

    @property
    def dd(self):
        return self._dynamic

    @property
    def sd(self):
        return self._static

#DC = DataContext()

