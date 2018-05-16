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
building_placer = 'naive_predef'  # 'naive_predef' | 'hybrid'
building_placer_verbose = 0
resource_verbose = 0
scout_explore_version = 0
combat_strategy = 'REFORM'  # 'REFORM' | 'HARASS'
production_strategy = 'RUSH'  # 'RUSH' | 'ADV_ARMS'
default_micro_version = 1
game_version = '3.16.1'  # '3.16.1' | '4.0'
