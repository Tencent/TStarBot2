""" geometry utilities """
from math import cos
from math import sin
from math import atan2
from math import sqrt


def polar_to_cart(rho, theta):
  return rho * cos(theta), rho * sin(theta)


def cart_to_polar(x, y):
  return sqrt(x * x + y * x), atan2(y, x)


def dist(unit1, unit2):
  """ return Euclidean distance ||unit1 - unit2|| """
  return ((unit1.float_attr.pos_x - unit2.float_attr.pos_x) ** 2 +
          (unit1.float_attr.pos_y - unit2.float_attr.pos_y) ** 2) ** 0.5


def dist_to_pos(unit, pos):
  """ return Euclidean distance ||unit - [x,y]|| """
  return ((unit.float_attr.pos_x - pos[0]) ** 2 +
          (unit.float_attr.pos_y - pos[1]) ** 2) ** 0.5


def list_mean(l):
  if not l:
    return None
  return sum(l) / float(len(l))


def mean_pos(units):
  if not units:
    return ()
  xx = [u.float_attr.pos_x for u in units]
  yy = [u.float_attr.pos_y for u in units]
  return list_mean(xx), list_mean(yy)