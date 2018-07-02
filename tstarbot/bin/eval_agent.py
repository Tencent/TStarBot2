"""evaluate an agent. Adopted from pysc2.bin.agent"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import importlib
import time

from pysc2 import maps
from pysc2.env import sc2_env
from pysc2.lib import stopwatch
from absl import app
from absl import flags


races = {
  "R": sc2_env.Race.random,
  "P": sc2_env.Race.protoss,
  "T": sc2_env.Race.terran,
  "Z": sc2_env.Race.zerg,
}

difficulties = {
  "1": sc2_env.Difficulty.very_easy,
  "2": sc2_env.Difficulty.easy,
  "3": sc2_env.Difficulty.medium,
  "4": sc2_env.Difficulty.medium_hard,
  "5": sc2_env.Difficulty.hard,
  "6": sc2_env.Difficulty.hard,
  "7": sc2_env.Difficulty.very_hard,
  "8": sc2_env.Difficulty.cheat_vision,
  "9": sc2_env.Difficulty.cheat_money,
  "A": sc2_env.Difficulty.cheat_insane,
}

FLAGS = flags.FLAGS
flags.DEFINE_bool("render", True, "Whether to render with pygame.")
flags.DEFINE_string("agent1", "Bot",
                    "Agent for player 1 ('Bot' for internal AI)")
flags.DEFINE_string("agent1_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_string("agent2", None,
                    "Agent for player 2 ('Bot' for internal AI, None for one player map.)")
flags.DEFINE_string("agent2_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")

flags.DEFINE_enum("agent1_race", 'Z', races.keys(), "Agent1's race.")
flags.DEFINE_enum("agent2_race", 'Z', races.keys(), "Agent2's race.")
flags.DEFINE_string("difficulty", "A",
                    "Bot difficulty (from '1' to 'A')")

flags.DEFINE_integer("screen_resolution", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("minimap_resolution", 64,
                     "Resolution for minimap feature layers.")
flags.DEFINE_float("screen_ratio", "1.33",
                   "Screen ratio of width / height")
flags.DEFINE_string("agent_interface_format", "feature",
                    "Agent Interface Format: [feature|rgb]")

flags.DEFINE_integer("max_agent_episodes", 3, "Total agent episodes.")
flags.DEFINE_integer("game_steps_per_episode", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")
flags.DEFINE_integer("random_seed", None, "Random_seed used in game_core.")

flags.DEFINE_bool("disable_fog", False, "Turn off the Fog of War.")
flags.DEFINE_bool("profile", False, "Whether to turn on code profiling.")
flags.DEFINE_bool("trace", False, "Whether to trace the code execution.")
flags.DEFINE_integer("parallel", 2, "How many instances to run in parallel.")

flags.DEFINE_bool("save_replay", True, "Whether to save a replay at the end.")

flags.DEFINE_string("map", None, "Name of a map to use.")
flags.mark_flag_as_required("map")


def run_loop(agents, env, max_episodes=1):
  """A run loop to have agents and an environment interact."""
  me_id = 0
  total_frames = 0
  n_episode = 0
  n_win = 0
  result_stat = [0] * 3  # n_draw, n_win, n_loss
  start_time = time.time()

  action_spec = env.action_spec()
  observation_spec = env.observation_spec()
  for agent, obs_spec, act_spec in zip(agents, observation_spec, action_spec):
    agent.setup(obs_spec, act_spec)

  try:
    while True:
      timesteps = env.reset()
      for a in agents:
        a.reset()

      # run this episode
      while True:
        total_frames += 1
        actions = [agent.step(timestep) for agent, timestep in
                   zip(agents, timesteps)]
        timesteps = env.step(actions)
        if timesteps[me_id].last():
          result_stat[timesteps[0].reward] += 1
          break

      # update
      n_episode += 1

      # print info
      outcome = timesteps[me_id].reward
      if outcome > 0:
        n_win += 1
      elif outcome == 0:
        n_win += 0.5

      win_rate = n_win / n_episode
      print(
        'episode = {}, outcome = {}, n_win = {}, '
        'current winning rate = {}'.format(n_episode, outcome, n_win, win_rate)
      )

      # done?
      if n_episode >= max_episodes:
        break
  except KeyboardInterrupt:
    pass
  finally:
    elapsed_time = time.time() - start_time
    print("Took %.3f seconds for %s steps: %.3f fps" % (
      elapsed_time, total_frames, total_frames / elapsed_time))


def run_thread(players, agents, map_name, visualize):
  rs = FLAGS.random_seed
  if FLAGS.random_seed is None:
    rs = int((time.time() % 1) * 1000000)
  print("Random seed: {}.".format(rs))
  screen_res = (int(FLAGS.screen_ratio * FLAGS.screen_resolution) // 4 * 4,
                FLAGS.screen_resolution)
  if FLAGS.agent_interface_format == 'feature':
    agent_interface_format = sc2_env.AgentInterfaceFormat(
      feature_dimensions=sc2_env.Dimensions(
        screen=screen_res,
        minimap=FLAGS.minimap_resolution))
  elif FLAGS.agent_interface_format == 'rgb':
    agent_interface_format = sc2_env.AgentInterfaceFormat(
      rgb_dimensions=sc2_env.Dimensions(
        screen=screen_res,
        minimap=FLAGS.minimap_resolution))
  else:
    raise NotImplementedError
  with sc2_env.SC2Env(
      map_name=map_name,
      players=players,
      step_mul=FLAGS.step_mul,
      random_seed=rs,
      game_steps_per_episode=FLAGS.game_steps_per_episode,
      agent_interface_format=agent_interface_format,
      score_index=-1,  # this indicates the outcome is reward
      disable_fog=FLAGS.disable_fog,
      visualize=visualize) as env:

    run_loop(agents, env, max_episodes=FLAGS.max_agent_episodes)
    if FLAGS.save_replay:
      env.save_replay("%s vs. %s" % (FLAGS.agent1, FLAGS.agent2))


def get_agent(agt_path, config_path=""):
  agent_module, name = agt_path.rsplit('.', 1)
  agt_cls = getattr(importlib.import_module(agent_module), name)
  agent_kwargs = {}
  if config_path:
    agent_kwargs['config_path'] = config_path
  agent = agt_cls(**agent_kwargs)
  return agent


def main(unused_argv):
  """Run an agent."""
  stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
  stopwatch.sw.trace = FLAGS.trace

  maps.get(FLAGS.map)  # Assert the map exists.
  players = []
  agents = []
  bot_difficulty = difficulties[FLAGS.difficulty]
  if FLAGS.agent1 == 'Bot':
    players.append(sc2_env.Bot(races['Z'], bot_difficulty))
  else:
    players.append(sc2_env.Agent(races[FLAGS.agent1_race]))
    agents.append(get_agent(FLAGS.agent1, FLAGS.agent1_config))
  if FLAGS.agent2 is None:
    pass
  elif FLAGS.agent2 == 'Bot':
    players.append(sc2_env.Bot(races['Z'], bot_difficulty))
  else:
    players.append(sc2_env.Agent(races[FLAGS.agent2_race]))
    agents.append(get_agent(FLAGS.agent2, FLAGS.agent2_config))

  run_thread(players, agents, FLAGS.map, FLAGS.render)

  if FLAGS.profile:
    print(stopwatch.sw)


def entry_point():  # Needed so setup.py scripts work.
  app.run(main)


if __name__ == "__main__":
  app.run(main)
