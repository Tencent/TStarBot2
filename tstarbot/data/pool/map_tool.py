import numpy as np
from PIL import Image
from queue import Queue
import copy

def bitmap2array(image):
    array = np.frombuffer(image.data, dtype=np.uint8)
    array = np.reshape(array, (image.size.y, image.size.x))
    array = copy.copy(array[::-1].transpose())
    return array

def save_image(image, figure_name):
    array = np.frombuffer(image.data, dtype=np.uint8)
    array = np.reshape(array, (image.size.y, image.size.x))
    im = Image.fromarray(array, mode='L')
    im = im.convert('RGB')
    im.save(figure_name)

def compute_dist(x, y, array):
    q = Queue()
    q.put((x,y))
    nx, ny = array.shape
    dist = -np.ones(array.shape, dtype=np.int16)
    dist[x,y] = 0
    dx = [-1, 1, 0, 0]
    dy = [0, 0, -1, 1]
    while not q.empty():
        x_now, y_now = q.get()
        for i in range(4):
            x_next = x_now + dx[i]
            y_next = y_now + dy[i]
            if x_next>=0 and x_next<nx and y_next>=0 and y_next<ny:
                if dist[x_next, y_next] == -1 and array[x_next, y_next] == 0:
                    dist[x_next, y_next] = dist[x_now, y_now] + 1
                    q.put((x_next, y_next))
    return dist

def compute_area_dist(areas, timestep, pos):
    """ distance from area.ideal_base_pos to pos """
    pathing_grid = timestep.game_info.start_raw.pathing_grid
    array = bitmap2array(pathing_grid)
    dist = {}
    # erase base in pathing_grid
    for area in areas:
        pos_area = area.ideal_base_pos
        if array[int(pos_area[0]), int(pos_area[1])] !=0:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    array[int(pos_area[0]) + dx,
                          int(pos_area[1]) + dy] = 0
    # compute map distance from area.ideal_base_pos to pos
    d = compute_dist(int(pos[0]),
                     int(pos[1]), array)
    for area in areas:
        pos_area = area.ideal_base_pos
        dist[area] = d[int(pos_area[0]), int(pos_area[1])]
    return dist

class Slope(object):
    def __init__(self, mean_x, mean_y, size, min_height, max_height, pos, h):
        self.x = mean_x
        self.y = mean_y
        self.size = size
        self.min_h = min_height
        self.max_h = max_height
        self.pos = pos # [(x1, y1), (x2, y2), ... , (xn, yn)]
        self.height = h # [H1, H2, ... , Hn]

def get_slopes(timestep):
    """ get all the slopes in map """
    pathing_grid = timestep.game_info.start_raw.pathing_grid
    placement_grid = timestep.game_info.start_raw.placement_grid
    terrain_height = timestep.game_info.start_raw.terrain_height
    pathing = bitmap2array(pathing_grid)
    placement = bitmap2array(placement_grid)
    height = bitmap2array(terrain_height)

    slopes = []
    for i in range(pathing_grid.size.x):
        for j in range(pathing_grid.size.y):
            if pathing[i, j] == 0 and placement[i, j] == 0:
                slope_item = extract_slope(i, j, pathing, placement, height)
                if slope_item.min_h != slope_item.max_h:
                    slopes.append(slope_item)
    return slopes

def extract_slope(x, y, pathing, placement, height):
    q = Queue()
    q.put((x,y))
    pathing[x, y] = 255
    nx, ny = pathing.shape
    pos = [(x, y)]
    h = height[x,y]
    heights = [h]
    sum_x = x
    sum_y = y
    num = 1
    max_h = h
    min_h = h
    dx = [-1, 1, 0, 0]
    dy = [0, 0, -1, 1]
    while not q.empty():
        x_now, y_now = q.get()
        for i in range(4):
            x_next = x_now + dx[i]
            y_next = y_now + dy[i]
            if x_next>=0 and x_next<nx and y_next>=0 and y_next<ny:
                if pathing[x_next, y_next] == 0 and placement[x_next, y_next] == 0:
                    pathing[x_next, y_next] = 255
                    q.put((x_next, y_next))
                    pos.append((x_next, y_next))
                    sum_x += x_next
                    sum_y += y_next
                    num += 1
                    h = height[x_next, y_next]
                    heights.append(h)
                    max_h = max(h, max_h)
                    min_h = min(h, min_h)
    return Slope(sum_x/num, sum_y/num, num, min_h, max_h, pos, heights)