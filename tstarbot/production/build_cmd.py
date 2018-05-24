from collections import namedtuple


BuildCmdBuilding = namedtuple('build_cmd_building', ['base_tag', 'unit_type'])
BuildCmdUnit = namedtuple('build_cmd_unit', ['base_tag', 'unit_type'])
BuildCmdUpgrade = namedtuple('build_cmd_upgrade', ['building_tag',
                                                   'ability_id'])
BuildCmdMorph = namedtuple('build_cmd_morph', ['unit_tag',
                                               'ability_id'])
BuildCmdExpand = namedtuple('build_cmd_expand', ['base_tag', 'pos',
                                                 'builder_tag'])
BuildCmdHarvest = namedtuple('build_cmd_harvest', ['gas_first'])
BuildCmdSpawnLarva = namedtuple('build_cmd_spawn_larva',
                                ['base_tag', 'queen_tag'])