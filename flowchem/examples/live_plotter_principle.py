"""
Simple script with two asyncio tasks representing the conceptual approach to live plotting
e.g. for FlowIR results. Trivially extendable with a third task to auto-save results.
"""
import asyncio
import random

data_history_for_plot = []


async def get_data():
    while True:
        new_datapoint = random.random()
        data_history_for_plot.append(new_datapoint)
        print(f"Got {new_datapoint}!")
        await asyncio.sleep(1)


async def plot_data():
    while True:
        print(f"The list now contains {data_history_for_plot}!")
        await asyncio.sleep(2)

loop = asyncio.get_event_loop()
loop.create_task(get_data())
loop.create_task(plot_data())
loop.run_forever()
