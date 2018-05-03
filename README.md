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
pillow (for optional image saving)
```
All the dependencies will be automatically installed with the `pip install` command.

## How to Run
Run the agent using `pysc2.bin.agent`. Example:

```
python -m pysc2.bin.agent \
    --map DefeatRoaches \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --screen_resolution 64 \
    --agent_race T \
    --bot_race Z
```
See more examples [here](docs/examples_howtorun.md).

## Evaluate
Evaluate the agent (e.g., winning rate) using `tstarbot.bin.eval_agent`. Example:
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
See more examples [here](docs/examples_evaluate.md).

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

## Coding Style
Use the google python coding style:
http://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules/
