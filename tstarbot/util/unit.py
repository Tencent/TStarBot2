""" units collecting/finding utilities """
import numpy as np
from tstarbot.util.geom import dist_to_pos

from .geom import dist


def collect_units_by_type_alliance(units, unit_type, alliance=1):
  """ return units with the specified unit type and alliance """
  return [u for u in units
          if u.unit_type == unit_type and u.int_attr.alliance == alliance]


def collect_units_by_tags(units, tags):
  uu = []
  for tag in tags:
    u = find_by_tag(units, tag)
    if u:
      uu.append(u)
  return uu


def find_by_tag(units, tag):
  for u in units:
    if u.tag == tag:
      return u
  return None


def find_nearest_l1(units, unit):
  """ find the nearest one (in l1-norm) to 'unit' within the list 'units' """
  if not units:
    return None
  x, y = unit.float_attr.pos_x, unit.float_attr.pos_y
  dd = np.asarray([
    abs(u.float_attr.pos_x - x) + abs(u.float_attr.pos_y - y) for
    u in units])
  return units[dd.argmin()]


def find_nearest_to_pos(units, pos):
  """ find the nearest one to pos within the list 'units' """
  if not units:
    return None
  dd = np.asarray([dist_to_pos(u, pos) for u in units])
  return units[dd.argmin()]


def find_nearest(units, unit):
  """ find the nearest one (in l2-norm) to 'unit' within the list 'units' """
  x, y = unit.float_attr.pos_x, unit.float_attr.pos_y
  return find_nearest_to_pos(units, [x, y])


def find_first_if(units, f=lambda x: True):
  for u in units:
    if f(u):
      return u
  return None


def find_n_if(units, n, f=lambda x: True):
  ru = []
  for u in units:
    if len(ru) >= n:
      break
    if f(u):
      ru.append(u)
  return ru


def sort_units_by_distance(units, unit):
  def my_dist(x_u):
    return dist(x_u, unit)

  return sorted(units, key=my_dist)

