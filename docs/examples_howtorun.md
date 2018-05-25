# Examples: How-to-Run

## AI vs Builtin Bot 
```
python -m pysc2.bin.agent \
    --map DefeatRoaches \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --screen_resolution 64 \
    --agent_race T \
    --bot_race Z
```

```
python -m pysc2.bin.agent \
    --map Simple64 \
    --agent tstarbot.agents.dancing_drones_agent.DancingDronesAgent \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z
```

```
python -m pysc2.bin.agent \
    --map Simple64 \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z
```

## Human vs AI
The following command starts two windows that 
you can play (with mouse) in one window:
```
python -m tstarbot.sandbox.py_multiplayer \
    --map AbyssalReef \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --agent1_config tstarbot.agents.dft_config \
    --agent1_race Z \
    --agent2_race Z
```

## AI vs AI
```
python -m tstarbot.sandbox.py_multiplayer \
    --map AbyssalReef \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --agent1_config tstarbot.agents.dft_config \
    --agent1_race Z \
    --agent2 tstarbot.agents.zerg_agent.ZergAgent \
    --agent2_config tstarbot.agents.dft_config \
    --agent2_race Z
```
