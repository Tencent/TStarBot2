# TStarBot

A Star Craft II bot. Compatible with `pysc2.agents` (i.e., it can be run by `pysc2.bin.agent`).

## Install
cd to the folder and run the command:
```
pip install -e .
```

## Dependencies
```
pysc2 (Zheng Yang's fork)
```

## How to Run
Examples:

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

## Evaluate
Evaluate the agent (e.g., winning rate) using `tstarbot.bin.eval_agent`. Examples:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map AbyssalReef \
    --difficulty 3 \
    --norender \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z
```

```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map AbyssalReef \
    --difficulty 8 \
    --render \
    --agent pysc2.agents.random_agent.RandomAgent \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z
```

## Profiling
Use `pysc2.lib.stopwatch` to profile the code. 
As an example, see `tstarbot/agents/micro_defeat_roaches_agent.py` and run the following command:
```
python -m pysc2.bin.agent \
    --map DefeatRoaches \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --screen_resolution 64 \
    --agent_race T \
    --bot_race Z \
    --profile
```