import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Time 2.5, 5.0, 7.5, 10, 12.5, 15
time = np.linspace(25, 150, 6)
time = time / 10

# Temp 50, 60, 70, 80, 90
temp = np.linspace(50, 90, 5)

# Data
df = pd.DataFrame.from_dict(
    {
        "2.5": [0, 1, 2, 4, 8],
        "5": [2, 4, 8, 16, 32],
        "7.5": [4, 1, 2, 4, 8],
        "10": [6, 1, 2, 4, 8],
        "12.5": [8, 20, 50, 70, 90],
        "15": [20, 50, 70, 90, 100],
    },
)
df.index.name = "time"
df.columns.name = "temp"

with plt.xkcd():
    fig, ax = plt.subplots()
    plt.pcolormesh(time, temp, np.array(df))
    ax.set_title("Fake data :D")
    ax.set_xlabel("Time (min)")
    ax.set_ylabel("Temp (C)")
    ax.set_xticks([2.5, 5, 7.5, 10, 12.5, 15])
    fig.tight_layout()
    plt.show()
