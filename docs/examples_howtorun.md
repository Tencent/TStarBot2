# Examples: How-to-Run

## AI vs Builtin Bot
Mini-games:
```
python -m pysc2.bin.agent \
    --map DefeatRoaches \
    --feature_screen_size 64 \
    --agent tstarbot.agents.micro_defeat_roaches_agent.MicroDefeatRoachesAgent \
    --agent_race terran \
    --agent2 Bot \
    --agent2_race zerg
```

```
python -m pysc2.bin.agent \
    --map Simple64 \
    --feature_screen_size 64 \
    --agent tstarbot.agents.dancing_drones_agent.DancingDronesAgent \
    --agent_race zerg \
    --agent2 Bot \
    --agent2_race zerg
```

Full 1v 1 game:
```
python -m pysc2.bin.agent \
    --map Simple64 \
    --feature_screen_size 64 \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_race zerg \
    --agent2 Bot \
    --agent2_race zerg
```

## AI vs AI
See how two AIs play against each other:
```
python -m pysc2.bin.agent \
    --map AbyssalReef \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_race zerg \
    --agent2 pysc2.agents.random_agent.RandomAgent \
    --agent2_race zerg
```

See how the AI performs "self-play":
```
python -m pysc2.bin.agent \
    --map AbyssalReef \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_race zerg \
    --agent2 tstarbot.agents.zerg_agent.ZergAgent \
    --agent2_race zerg
```

## Human vs AI
Here is a simple example of playing against AI in a single machine
(See more details in the doc of `pysc2.bin.play_vs_agent`).  

First, run:
```
python -m pysc2.bin.play_vs_agent \
    --human \
    --map AbyssalReef \
    --user_race zerg
```
to host a game.

Then run the following command in another process (terminal)
```
python -m pysc2.bin.play_vs_agent \
    --agent tstarbot.agents.zerg_agent.ZergAgent \
    --agent_race zerg
```
to let the AI join the game.

