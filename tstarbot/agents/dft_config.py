""" A default template config file for an agent.

Treat it as a plain py file.
Define the required configurations in "flat structure", e.g.,
var1 = value1
var2 = value2
...

Do NOT ABUSE it, do NOT define nested or complex data structure.
"""
sleep_per_step = 0.0
building_verbose = 0
building_placer = 'hybrid_v2'  # 'naive_predef' | 'hybrid' | 'hybrid_v2'
building_placer_verbose = 2
resource_verbose = 0
production_verbose = 0
scout_explore_version = 2
max_forced_scout_count = 0  # num of drones used to scout
combat_strategy = 'HARASS'  # 'REFORM' | 'HARASS'
production_strategy = 'DEF_AND_ADV'  # 'RUSH' | 'ADV_ARMS' | 'DEF_AND_ADV'
default_micro_version = 1
game_version = '3.16.1' # '3.16.1' | '4.3'
