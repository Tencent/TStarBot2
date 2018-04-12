import numpy as np
from PIL import Image
from queue import Queue
import copy

def bitmap2array(image):
    array = np.frombuffer(image.data, dtype=np.uint8)
    array = np.reshape(array, (image.size.y, image.size.x))
    array = copy.copy(array[::-1].transpose())
    return array

def save_image(image):
    array = np.frombuffer(image.data, dtype=np.uint8)
    array = np.reshape(array, (image.size.y, image.size.x))
    im = Image.fromarray(a, mode='L')
    im = im.convert('RGB')
    im.save('temp.png')

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
