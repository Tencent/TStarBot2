# Examples: Evaluate

## Full Games
Evaluate an agent on full game:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map AbyssalReef \
    --render \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --screen_resolution 64 \
    --agent1_race Z \
    --agent2 Bot \
    --agent2_race Z \
    --difficulty 8
```

One can pass in agent config file (when supported by the agent):
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 5 \
    --map Simple64 \
    --render \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --agent1_config tstarbot.agents.dft_config \
    --screen_resolution 64 \
    --agent1_race Z \
    --agent2 Bot \
    --agent2_race Z \
    --difficulty 5 \
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
A well configured agent plays against Difficulty-A (cheat_insane) builtin bot:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 1 \
    --step_mul 4 \
    --map AbyssalReef \
    --norender \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --agent1_config tstarbot.agents.dft_config \
    --screen_resolution 64 \
    --agent1_race Z \
    --agent2 Bot \
    --agent2_race Z \
    --nodisable_fog \
    --difficulty A
```

## AI against AI
Two well configured agents plays against each other:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 1 \
    --step_mul 4 \
    --map AbyssalReef \
    --norender \
    --agent1 tstarbot.agents.zerg_agent.ZergAgent \
    --agent1_config tstarbot.agents.dft_config \
    --agent2 tstarbot.agents.zerg_agent.ZergAgent \
    --agent2_config tstarbot.agents.dft_config \
    --screen_resolution 64 \
    --agent1_race Z \
    --agent2_race Z \
    --nodisable_fog
```

## Mini Games
One can also evaluate an agent over Mini Game. Example:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 15 \
    --map DefeatRoaches \
    --norender \
    --agent1 tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --screen_resolution 64 \
    --agent1_race T 
```
which should achieve an almost 100% winning rate. 

As a comparison, the Deempmind baseline agent rarely wins:
```
python -m tstarbot.bin.eval_agent \
    --max_agent_episodes 15 \
    --map DefeatRoaches \
    --norender \
    --agent1 pysc2.agents.scripted_agent.DefeatRoaches \
    --screen_resolution 64 \
    --agent1_race T 
```