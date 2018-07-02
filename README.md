# TStarBot

A rule-based Star Craft II bot. Compatible with `pysc2.agents`.

## Install
cd to the folder and run the command:
```
pip install -e .
```

## Dependencies
```
pysc2 (Zheng Yang's fork)
pillow
```
All the dependencies will be automatically installed with the `pip install` command.

## How to Run
Run the agent using the scripts from `pysc2.bin`. 
Example:

```
python -m pysc2.bin.agent \
    --map AbyssalReef \
    --feature_screen_size 64 \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_race zerg \
    --agent2 Bot \
    --agent2_race zerg
```
See more examples [here](docs/examples_howtorun.md).

## Evaluate
Evaluate the agent (e.g., winning rate) using `tstarbot.bin.eval_agent`. 
Example:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map AbyssalReef \
    --norender \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --screen_resolution 64 \
    --agent1_race Z \
    --agent2 Bot \
    --agent2_race Z \
    --difficulty 3
```
See more examples [here](docs/examples_evaluate.md). 
In particular, see how a well configured agent plays against 
difficulty-A (cheat_insane) builtin bot [here](docs/examples_evaluate.md#against-difficulty-a-builtin-bot). 

## Profiling
Use `pysc2.lib.stopwatch` to profile the code. 
As an example, see `tstarbot/agents/micro_defeat_roaches_agent.py` and run the following command:
```
python -m pysc2.bin.agent \
    --map DefeatRoaches \
    --feature_screen_size 64 \
    --max_episodes 2 \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --agent_race terran \
    --agent2 Bot \
    --agent2_race zerg \
    --profile
```

## AI-vs-AI and Human-vs-AI 
See examples [here](docs/examples_howtorun.md#ai-vs-ai).

## Coding Style
Be consistent with that of `pysc2`.
