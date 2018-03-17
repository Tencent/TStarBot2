# Examples: How-to-Run
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