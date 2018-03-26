from enum import Enum, unique
from pysc2.lib.typeenums import RACE, UNIT_TYPEID, ABILITY_ID, UPGRADE_ID, BUFF_ID

@unique
class WorkerState(Enum):
  IDLE = 0
  MINERALS = 1
  GAS = 2
  BUILD = 3
  COMBAT = 4
  MOVE = 5
  SCOUT = 6
  REPAIR = 7
  DEFAULT = 8

@unique
class WorkerSubState(Enum):
  pass 

@unique
class AllianceType(Enum):
  SELF = 1
  ALLY = 2
  NEUTRAL = 3
  ENEMY = 4


WORKER_UNITS = set([UNIT_TYPEID.ZERG_DRONE.value])
BASE_UNITS = set([UNIT_TYPEID.ZERG_HATCHERY.value])
MINIERAL_UNITS = set([UNIT_TYPEID.NEUTRAL_RICHMINERALFIELD.value,
                      UNIT_TYPEID.NEUTRAL_RICHMINERALFIELD750.value, 
                      UNIT_TYPEID.NEUTRAL_MINERALFIELD.value, 
                      UNIT_TYPEID.NEUTRAL_MINERALFIELD750.value,
                      UNIT_TYPEID.NEUTRAL_LABMINERALFIELD.value,
                      UNIT_TYPEID.NEUTRAL_LABMINERALFIELD750.value,
                      UNIT_TYPEID.NEUTRAL_PURIFIERRICHMINERALFIELD.value,
                      UNIT_TYPEID.NEUTRAL_PURIFIERRICHMINERALFIELD750.value,
                      UNIT_TYPEID.NEUTRAL_PURIFIERMINERALFIELD.value,
                      UNIT_TYPEID.NEUTRAL_PURIFIERMINERALFIELD750.value,
                      UNIT_TYPEID.NEUTRAL_BATTLESTATIONMINERALFIELD.value,
                      UNIT_TYPEID.NEUTRAL_BATTLESTATIONMINERALFIELD750.value])

VESPENE_UNITS = set([UNIT_TYPEID.NEUTRAL_VESPENEGEYSER.value,
                     UNIT_TYPEID.NEUTRAL_SPACEPLATFORMGEYSER.value,
                     UNIT_TYPEID.NEUTRAL_RICHVESPENEGEYSER.value])

VESPENE_BUILDING_UNITS = set([UNIT_TYPEID.ZERG_EXTRACTOR.value])

WORKER_RESOURCE_ABILITY = set([ABILITY_ID.HARVEST_GATHER_DRONE.value,
                               ABILITY_ID.HARVEST_RETURN_DRONE.value])

WORKER_BUILD_ABILITY = set([ABILITY_ID.BUILD_HATCHERY.value,
                            ABILITY_ID.BUILD_EVOLUTIONCHAMBER.value,
                            ABILITY_ID.BUILD_EXTRACTOR.value,
                            ABILITY_ID.BUILD_HYDRALISKDEN.value,
                            ABILITY_ID.BUILD_SPAWNINGPOOL.value,
                            ABILITY_ID.BUILD_SPIRE.value,
                            ABILITY_ID.BUILD_ULTRALISKCAVERN.value,
                            ABILITY_ID.BUILD_BANELINGNEST.value,
                            ABILITY_ID.BUILD_INFESTATIONPIT.value,
                            ABILITY_ID.BUILD_NYDUSNETWORK.value,
                            ABILITY_ID.BUILD_ROACHWARREN.value,
                            ABILITY_ID.BUILD_SPINECRAWLER.value,
                            ABILITY_ID.BUILD_SPORECRAWLER.value])

WORKER_MOVE_ABILITY = set([UNIT_TYPEID.ZERG_CHANGELINGZERGLINGWINGS.value,
                           UNIT_TYPEID.ZERG_CHANGELINGZERGLING.value, 
                           UNIT_TYPEID.TERRAN_COMMANDCENTER.value,
                           UNIT_TYPEID.TERRAN_SUPPLYDEPOT.value, 
                           UNIT_TYPEID.TERRAN_REFINERY.value])

WORKER_COMBAT_ABILITY = set([])

if __name__ == '__main__':
    print(WORKER_UNITS)
    print(BASE_UNITS)
    print(MINIERAL_UNITS)
    print(VESPENE_UNITS)
    print(VESPENE_BUILDING_UNITS)
    print(WORKER_RESOURCE_ABILITY)
    print(WORKER_MOVE_ABILITY)
    print(WORKER_BUILD_ABILITY)
    print(WORKER_COMBAT_ABILITY)
