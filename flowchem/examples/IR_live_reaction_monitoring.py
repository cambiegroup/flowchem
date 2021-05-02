import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

style.use("seaborn-dark")

fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
reaction_time = []
reaction_yield = []


def animate(i):
    ax1.clear()
    ax1.plot(reaction_time, reaction_yield)

# Main animation loop
ani = animation.FuncAnimation(fig, animate, 1000)
plt.show()
