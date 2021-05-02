"""
Simple script with two asyncio tasks representing the conceptual approach to live plotting
e.g. for FlowIR results. Trivially extendable with a third task to auto-save results.
"""
import asyncio
import random
from matplotlib import style
import matplotlib.pyplot as plt

data_history_for_plot = []

# PLOT SETUP
style.use("seaborn-dark")
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)


async def get_data():
    while True:
        ax1.clear()
        ax1.scatter(range(len(data_history_for_plot)), data_history_for_plot)
        plt.pause(0.1)
        print(f"update plot! {data_history_for_plot}")
        await asyncio.sleep(1)


async def plot_data():
    while True:
        new_datapoint = random.random()
        data_history_for_plot.append(new_datapoint)
        print(f"The list now contains {data_history_for_plot}!")
        await asyncio.sleep(2)

loop = asyncio.get_event_loop()
loop.create_task(get_data())
loop.create_task(plot_data())
loop.run_forever()
