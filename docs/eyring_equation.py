""" Graph for Eyring equation.

(c) Dario Cambié 2020 - to be used in grant applications
"""
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.constants import Boltzmann, Planck, gas_constant
from matplotlib.colors import LogNorm
from matplotlib.ticker import FixedLocator, FuncFormatter

CONTOURS_COLOR = "k"  # black
COLORMAP = "coolwarm"  # Other good ones: coolwarm Blues


def c_to_k(temp_in_c: float) -> float:
    """ Converts Celsius to Kelvin """
    return temp_in_c + 273.15


def eyring_eq(temperature_in_c: float, time: float) -> float:
    """
    Eyring equation reversed to explicit DeltaG and t1/2
    See Synthesis review on MOC for details on formula, but essentially it is Arrhenius
    t_{1/2} = ln(2) / k_{rac}
    k_{rac} = 2*(kT/h)*exp(-DeltaG/RT)

    :param temperature_in_c: temperature in K
    :param time: in seconds
    :return: Delta G in kCal / mol
    """

    k = Boltzmann  # units: J/K [1.380649×10−23]
    h = Planck  # units: J/s [6.62607015×10−34]
    R = gas_constant  # units: J/(K*mol)[8.314462618]
    T = c_to_k(temperature_in_c)  # Kelvin
    ln2 = math.log(2)

    J_over_mole = math.log(2 * k * T / h) * R * T - math.log(ln2 / time) * R * T
    return J_over_mole / 4184


# Axis range
xx, yy = np.meshgrid(np.linspace(-80, 30, 300), np.logspace(-2, 5, 200))

# Calculate values
zz = np.zeros(xx.shape)
for i in range(xx.shape[0]):
    for j in range(xx.shape[1]):
        zz[i, j] = eyring_eq(xx[i, j], yy[i, j])


# Set canvas for plot
fig, ax = plt.subplots()

# Title
# ax.set_title('Racemization barrier as function of racemization $t_{1/2}$ and temperature')

# Delta G levels for contour
levels = np.arange(10, 24, 2)
CS = ax.contour(xx, yy, zz, levels, colors=CONTOURS_COLOR,)

# TIME AXIS SETTINGS
plt.yscale("log")  # Log scale

# Time labels
annotate_time = {
    # 0.001: "1 ms",
    0.01: "10 ms",
    0.1: "100 ms",
    1: "1 s",
    10: "10 s",
    60: "1 min",
    600: "10 mins",
    3600: "1 hour",
    18000: "5 hours",
    86400: "1 day",
    604800: "1 week",
}
time_points = list(annotate_time.keys())


def label_time(time: float, pos=None) -> str:
    """ Given the time tick assign corresponding label"""
    return annotate_time.get(time, str(time))


# Set Locator and Formatter for time axis
ax.yaxis.set_major_locator(FixedLocator(time_points))
ax.yaxis.set_major_formatter(FuncFormatter(label_time))

# Y-axis on the right (left side needed for annotation in post-processing)
ax.yaxis.set_label_position("right")
ax.yaxis.tick_right()


# Y label
plt.ylabel(r"Racemization $t_{1/2}$")

# Contour labels (this have to be added after plt.yscale('log') for proper rendering)
lab = ax.clabel(CS, inline=1, fontsize=10, fmt="%2.0f $kcal/mol$")

# X label
plt.xlabel(r"Temperature ($\degree C$)")

# Add color gradient
plt.pcolor(xx, yy, zz, norm=LogNorm(), cmap=COLORMAP, shading="auto")

# Adjust position
plt.subplots_adjust(top=0.96, bottom=0.12, left=0.04, right=0.84, hspace=0.2, wspace=0.2)

# plt.show(); input()
plt.savefig("deltaG_vs_t_and_T.png", dpi=300)
