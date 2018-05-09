"""evaluate an agent. Adopted from pysc2.bin.agent"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import importlib
import threading

from future.builtins import range

from pysc2 import maps
from pysc2.env import sc2_env
from pysc2.lib import stopwatch

from absl import app
from absl import flags
import time

FLAGS = flags.FLAGS
flags.DEFINE_bool("render", True, "Whether to render with pygame.")
flags.DEFINE_integer("screen_resolution", 84,
                     "Resolution for screen feature layers.")
flags.DEFINE_integer("minimap_resolution", 64,
                     "Resolution for minimap feature layers.")

flags.DEFINE_integer("max_agent_episodes", 3, "Total agent episodes.")
flags.DEFINE_integer("game_steps_per_episode", 0, "Game steps per episode.")
flags.DEFINE_integer("step_mul", 8, "Game steps per agent step.")

flags.DEFINE_string("agent", "pysc2.agents.random_agent.RandomAgent",
                    "Which agent to run")
flags.DEFINE_string("agent_config", "",
                    "Agent's config in py file. Pass it as python module."
                    "E.g., tstarbot.agents.dft_config")
flags.DEFINE_enum("agent_race", None, sc2_env.races.keys(), "Agent's race.")
flags.DEFINE_enum("bot_race", None, sc2_env.races.keys(), "Bot's race.")
flags.DEFINE_enum("difficulty", None, sc2_env.difficulties.keys(),
                  "Bot's strength.")

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
    start_time = time.time()

    action_spec = env.action_spec()
    observation_spec = env.observation_spec()
    for agent in agents:
        agent.setup(observation_spec, action_spec)

    try:
        while True:
            timesteps = env.reset()
            for a in agents:
                a.reset()

            # run this episode
            while True:
                total_frames += 1
                actions = [agent.step(timestep) for agent, timestep in zip(agents, timesteps)]
                timesteps = env.step(actions)
                if timesteps[me_id].last():
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
            print('episode = {}, outcome = {}, n_win = {}, current winning rate = {}'.format(
                n_episode, outcome, n_win, win_rate))

            # done?
            if n_episode >= max_episodes:
                break
    except KeyboardInterrupt:
        pass
    finally:
        elapsed_time = time.time() - start_time
        print("Took %.3f seconds for %s steps: %.3f fps" % (
            elapsed_time, total_frames, total_frames / elapsed_time))


def run_thread(agent_cls, map_name, visualize):
    with sc2_env.SC2Env(
            map_name=map_name,
            agent_race=FLAGS.agent_race,
            bot_race=FLAGS.bot_race,
            difficulty=FLAGS.difficulty,
            step_mul=FLAGS.step_mul,
            game_steps_per_episode=FLAGS.game_steps_per_episode,
            screen_size_px=(FLAGS.screen_resolution, FLAGS.screen_resolution),
            minimap_size_px=(FLAGS.minimap_resolution, FLAGS.minimap_resolution),
            score_index=-1,  # this indicates the outcome is reward
            disable_fog=FLAGS.disable_fog,
            visualize=visualize) as env:
        agent_kwargs = {}
        if FLAGS.agent_config:
            agent_kwargs['config_path'] = FLAGS.agent_config
        agent = agent_cls(**agent_kwargs)
        run_loop([agent], env, max_episodes=FLAGS.max_agent_episodes)
        if FLAGS.save_replay:
            env.save_replay(agent_cls.__name__)


def main(unused_argv):
    """Run an agent."""
    stopwatch.sw.enabled = FLAGS.profile or FLAGS.trace
    stopwatch.sw.trace = FLAGS.trace

    maps.get(FLAGS.map)  # Assert the map exists.

    agent_module, agent_name = FLAGS.agent.rsplit(".", 1)
    agent_cls = getattr(importlib.import_module(agent_module), agent_name)

    run_thread(agent_cls, FLAGS.map, FLAGS.render)

    if FLAGS.profile:
        print(stopwatch.sw)


def entry_point():  # Needed so setup.py scripts work.
    app.run(main)


if __name__ == "__main__":
    app.run(main)
