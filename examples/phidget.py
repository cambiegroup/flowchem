import time
import matplotlib.pyplot as plt
from flowchem import PressureSensor

p_sens = PressureSensor(pressure_range=("0 bar", "25 bar"), vint_serial_number=627768, vint_channel=0)

start_time = time.time()
x = []
y = []
while True:
    x.append(time.time()-start_time)
    y.append(p_sens.read_pressure())
    plt.scatter(x, y)
    plt.show()
