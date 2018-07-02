"""Strategy Renderer."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import pygame


class Color(object):
  BLACK = (0, 0, 0)
  WHITE = (255, 255, 255)
  RED = (255, 0, 0)
  GREEN = (0, 255, 0)
  BLUE = (0, 0, 255)


class Renderer(object):
  def __init__(self, window_size, world_size, caption):
    pygame.init()
    pygame.display.set_caption(caption)
    self._surface = pygame.display.set_mode(window_size)
    self._window_size = window_size
    self._world_size = world_size
    self.clear()

  def __del__(object):
    pygame.quit()

  def draw_circle(self, color, world_pos, radias):
    pygame.draw.circle(self._surface, color, self._transform(world_pos),
                       int(radias))

  def draw_line(self, color, start_world_pos, end_world_pos, width=1):
    pygame.draw.line(self._surface, color, self._transform(start_world_pos),
                     self._transform(end_world_pos), width)

  def render(self):
    pygame.event.get()
    pygame.display.flip()

  def clear(self):
    self._surface.fill(Color.GREEN)

  def _transform(self, pos):
    x = pos['x'] / float(self._world_size['x']) * self._window_size[0]
    y = (1 - pos['y'] / float(self._world_size['y'])) * self._window_size[1]
    return (int(x), int(y))


class StrategyRenderer(Renderer):
  def draw(self, squads, enemy_clusters, commands):
    self.clear()
    for squad in squads:
      self._draw_squad(squad)
    for cluster in enemy_clusters:
      self._draw_enemy_cluster(cluster)
    for command in commands:
      self._draw_command(command)

  def _draw_squad(self, squad):
    self.draw_circle(Color.BLUE, squad.centroid, squad.num_units / 1.5 + 1)

  def _draw_enemy_cluster(self, cluster):
    self.draw_circle(Color.RED, cluster.centroid, cluster.num_units / 1.5 + 1)

  def _draw_command(self, command):
    self.draw_line(Color.BLACK, command.squad.centroid, command.position, 2)
