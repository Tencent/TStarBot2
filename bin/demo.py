from pysc2.env import sc2_env
import tstarbot as ts
from absl import app
from absl import flags
import os

os.environ["SC2PATH"] = "/Volumes/Macintosh2/Game/StarCraft II"

def demo(unused_argv):
  env = sc2_env.SC2Env(map_name='Simple64',
                       screen_size_px=(64, 64),
                       minimap_size_px=(64, 64),
                       agent_race='Z',
                       bot_race='Z',
                       difficulty=None,
                       step_mul=8,
                       game_steps_per_episode=0,
                       visualize=True)

  bot = ts.DemoBot(env)
  bot.setup()
  bot.run(100)


if __name__ == '__main__':
  app.run(demo)
