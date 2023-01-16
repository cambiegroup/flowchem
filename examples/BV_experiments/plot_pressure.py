import random
import time
from collections import deque
import matplotlib.pyplot as plt
import numpy as np
import requests

MINUTES = 2
pressure_history = deque([0.1]*60*MINUTES, maxlen=60*MINUTES)
x = list(range(120))

ax = plt.plot(x, pressure_history)


def update_plot():
    plt.clf()
    plt.plot(x, pressure_history)
    plt.draw()
    plt.pause(0.001)


while True:

    time.sleep(1)
    # endpoint = r"http://127.0.0.1:8000/r2/TwoPortValve_B/position"
    pressure_history.append(random.random())
    update_plot()


