# Examples: Evaluate

## Full Games
Evaluate an agent on full game:
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

One can pass in agent config file (if supported by the agent):
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map Simple64 \
    --difficulty 5 \
    --render \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_config tstarbot.agents.dft_config \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z \
    --disable_fog
```

One can turn-off rendering/visualization (on a headless server):
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

## Against Difficulty A Builtin Bot 
A well configured agent plays against Difficulty-A builtin bot:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 1 \
    --step_mul 4 \
    --map AbyssalReef \
    --difficulty A \
    --norender \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_config tstarbot.agents.dft_config \
    --screen_resolution 64 \
    --agent_race Z \
    --bot_race Z \
    --nodisable_fog
```

## Mini Games
One can also evaluate an agent over Mini Game. Example:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 15 \
    --map DefeatRoaches \
    --difficulty 3 \
    --norender \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --screen_resolution 64 \
    --agent_race T \
    --bot_race Z
```
which should achieve an almost 100% winning rate. 

As a comparison, the Deempmind baseline agent rarely wins:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 15 \
    --map DefeatRoaches \
    --difficulty 3 \
    --norender \
    --agent pysc2.agents.scripted_agent.DefeatRoaches \
    --screen_resolution 64 \
    --agent_race T \
    --bot_race Z
```