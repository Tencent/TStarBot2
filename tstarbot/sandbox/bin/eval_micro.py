from pysc2.env import sc2_env
from tstarbot.sandbox.agents.rule_micro_agent import MicroAgent
from absl import app
import os

os.environ["SC2PATH"] = "/home/psun/StarCraftII"


def demo(unused_argv):
    env = sc2_env.SC2Env(
        map_name='DefeatRoaches',
        screen_size_px=(64, 64),
        minimap_size_px=(64, 64),
        agent_race='T',
        bot_race='Z',
        difficulty=None,
        step_mul=1,
        game_steps_per_episode=0,
        visualize=True)  # visualize must be True to return unit information

    my_agent = MicroAgent(env)
    my_agent.setup()
    my_agent.run(1000000)


if __name__ == '__main__':
    app.run(demo)
