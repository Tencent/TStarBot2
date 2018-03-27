from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features
from s2clientprotocol import sc2api_pb2 as sc_pb
from pysc2.lib import typeenums as tp
import time
import random
# Functions
_TRAIN_DRONE = actions.FUNCTIONS.Train_Drone_quick.id
_TRAIN_OVERLORD = actions.FUNCTIONS.Train_Overlord_quick.id
_NOOP = actions.FUNCTIONS.no_op.id
_SELECT_POINT = actions.FUNCTIONS.select_point.id
_BUILD_SPAWNINGPOOL = actions.FUNCTIONS.Build_SpawningPool_screen.id
_TRAIN_ZERGLING = actions.FUNCTIONS.Train_Zergling_quick.id
_RALLY_UNITS_MINIMAP = actions.FUNCTIONS.Rally_Units_minimap.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id
_SELECT_LARVA = actions.FUNCTIONS.select_larva.id
train_command = {'drone':_TRAIN_DRONE, 'overlord':_TRAIN_OVERLORD,'zergling':_TRAIN_ZERGLING}
# Features
_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index

# Unit IDs
_ZERG_DRONE = 104 ## worker
_ZERG_EGG = 103
_ZERG_HATCHERY = 86 ## base
_ZERG_OVERLORD = 116 ## house
_ZERG_SPAWNINGPOOL = 89  ## Fen Lie Chi (Zergling)
_ZERG_ZERGLING = 119 

# Parameters
_PLAYER_SELF = 1
_SUPPLY_USED = 3
_SUPPLY_MAX = 4
_NOT_QUEUED = [0]
_QUEUED = [1]
_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index

class BaseItem(object):
    def __init__(self):
        self.base_tag = None
        self.bases = []
        self.workers = []
        self.larvas = []
        self.extractors = []
        self.minerals = []
        self.gas = []
        self.extractor_worker = {} # extractor_tag:[worker1, worker2,...]
        self.mineral_worker = {} # mineral_tag: [worker1,worker2]

    def update(self, units):
        self.workers = self.collect_unit(tp.UNIT_TYPEID.ZERG_DRONE.value, units)
        self.bases = self.collect_unit(tp.UNIT_TYPEID.ZERG_HATCHERY.value, units)
        self.larvas = self.collect_unit(tp.UNIT_TYPEID.ZERG_LARVA.value, units)
        self.minerals = self.collect_unit(tp.UNIT_TYPEID.NEUTRAL_MINERALFIELD.value, units, 16)
        self.gas = self.collect_unit(tp.UNIT_TYPEID.NEUTRAL_VESPENEGEYSER.value, units, 16)
        self.base_tag = self.bases[0].tag
        self.extractors = self.collect_unit(tp.UNIT_TYPEID.ZERG_EXTRACTOR.value, units)

    def collect_unit(self, unit_type, units, owner=1):
        unit_list = []
        for u in units:
            if u.unit_type == unit_type and u.int_attr.owner == owner:
                unit_list.append(u)
        return unit_list

class SimpleAgent(base_agent.BaseAgent):
    base_item = BaseItem()
    base_top_left = None
    overlord_built = False
    drone_selected = False
    spawningpool_built = False
    hatchery_selected = False
    hatchery_rallied = False
    army_selected = False
    army_rallied = False
    larva_selected = False
    drone = []
    hatchery = []
    larva = []
    zergling = []
    roach = []
    build_order = ['drone', 'drone','spawningpool','drone','overlord'] + ['zergling']*7 + ['overlord'] + ['zergling','zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling',  'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'zergling', 'overlord']* 1000
    k = 0
    def transformLocation(self, x, x_distance, y, y_distance):
        if not self.base_top_left:
            return [x - x_distance, y - y_distance]
        
        return [x + x_distance, y + y_distance]
    
    def reset(self):
       self.base_item = BaseItem()
       self.base_top_left = None
       self.overlord_built = False
       self.drone_selected = False
       self.spawningpool_built = False
       self.hatchery_selected = False
       self.hatchery_rallied = False
       self.army_selected = False
       self.army_rallied = False
       self.larva_selected = False
       self.k = 0
    
    def update(self, obs):
        units = obs.observation['units']
        self.base_item.update(units)
        self.hatchery = []
        self.drone =[]
        self.larva = []
        self.zergling = []
        self.roach = []
        for u in units:
            if u.unit_type == tp.UNIT_TYPEID.ZERG_HATCHERY.value:
                self.hatchery.append(u)
            if u.unit_type == tp.UNIT_TYPEID.ZERG_LARVA.value:
                self.larva.append(u)
            if u.unit_type == tp.UNIT_TYPEID.ZERG_DRONE.value:
                self.drone.append(u)
            if u.unit_type == tp.UNIT_TYPEID.ZERG_ZERGLING.value:
                self.zergling.append(u)
            #if u.unit_type == tp.UNIT_TYPEID.ZERG_ROACH.value:
            #    self.ROACH.append(u)

    def train_unit(self,obs,unit):
        if len(self.larva) == 0:
            return None, False
        action = sc_pb.Action()
        if unit == 'zergling':
            action.action_raw.unit_command.ability_id = tp.ABILITY_ID.TRAIN_ZERGLING.value
        elif obs.observation['player'][4] <= obs.observation['player'][3]+2:
            action.action_raw.unit_command.ability_id = tp.ABILITY_ID.TRAIN_OVERLORD.value
        action.action_raw.unit_command.unit_tags.append(self.larva[0].tag)
        return [action], True


    def step(self, obs):
        super(SimpleAgent, self).step(obs)
        if self.base_top_left is None:
            player_y, player_x = (obs.observation["minimap"][_PLAYER_RELATIVE] == _PLAYER_SELF).nonzero()
            self.base_top_left = player_y.mean() <= 31
        
        player_info = player_relative = obs.observation["player"]
        self.update(obs)
        print(self.base_item.minerals) 
        print(self.base_item.gas)
        if player_info[3]<100:#player_info[10]>0:
            if self.build_order[self.k] == 'spawningpool':
                if not self.drone_selected:
                    unit_type = obs.observation["screen"][_UNIT_TYPE]
                    unit_y, unit_x = (unit_type == _ZERG_DRONE).nonzero()
                
                    target = [unit_x[1], unit_y[1]]
                
                    self.drone_selected = True
                    return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])
                elif _BUILD_SPAWNINGPOOL in obs.observation["available_actions"]:
                    unit_type = obs.observation["screen"][_UNIT_TYPE]
                    unit_y, unit_x = (unit_type == _ZERG_HATCHERY).nonzero()
                    target = self.transformLocation(int(unit_x.mean()), 20, int(unit_y.mean()), 0)
                    #print(unit_x)
                    #print(self.hatchery)
                    self.spawningpool_built = True
                    self.drone_selected = False
                    self.k += 1
                    return actions.FunctionCall(_BUILD_SPAWNINGPOOL, [_NOT_QUEUED, target])
            else:
                action, trained = self.train_unit(obs, self.build_order[self.k])
                if trained:
                    self.k += 1
                if action != None:    
                    self.army_selected = False
                    return action

        if player_info[5]>10:
            #player_screen = obs.observation["screen"][_PLAYER_RELATIVE]
            player_minimap = obs.observation["minimap"][_PLAYER_RELATIVE]
            unit_y, unit_x = (player_minimap == 4).nonzero()
            if not self.army_selected:
                if _SELECT_ARMY in obs.observation["available_actions"]:
                    self.army_selected = True
                    self.hatchery_selected = False 
                return actions.FunctionCall(_SELECT_ARMY, [_NOT_QUEUED])
            elif _ATTACK_MINIMAP in obs.observation["available_actions"]:
                self.army_selected = False
                #if unit_y.any():
                #    target = [unit_x[0],unit_y[0]]
                if self.base_top_left:
                    if random.random()<0.6:
                        target = [39,45]
                    else:
                        target = [21,45]
                else:
                    if random.random()<0.6:
                        target = [21,24]
                    else:
                        target = [39,24]
                return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, target])
            
        return actions.FunctionCall(_NOOP, [])
