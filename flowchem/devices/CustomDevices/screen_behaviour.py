from flowchem.devices.CustomDevices.Peltier_cooler import (
    PeltierIO,
    PeltierCooler,
    PeltierDefaults,
    PeltierLowCoolingDefaults
)
from threading import Thread
import datetime
from pathlib import Path



from time import sleep

peltier_defaults = PeltierDefaults()
peltier_port = PeltierIO("COM4")
chiller = PeltierCooler(peltier_port, peltier_defaults, address=20)

stem="T_verification_fixedcode"
name=stem
done=False
def log_temperature(path=r"W:\BS-FlowChemistry\data\temp_log"):
    while True:
        current_T = chiller.get_temperature()
        current_t = datetime.datetime.now().strftime("%H:%M:%S")  #
        path_path = Path(path)
        with open(path_path / Path(name), "a") as f:
            f.write(f"{current_t};{current_T}\n")
        sleep(1)
        if done:
            break


tlog = Thread(target=log_temperature)
tlog.start()

chiller.start_control()
for p in range(20,-50,-10):
    print(f"Setting to {p}")
    chiller.set_temperature(p)
    print("Settling to temp")
    while abs(chiller.get_temperature() - p)>1:
        sleep(1)
    print("check for stability")
    print("log for 15 min")
    sleep(15*60)

for p in [-50,10,-30,0]:
    print(f"Setting to {p}")
    chiller.set_temperature(p)
    print("Settling to temp")
    while abs(chiller.get_temperature() - p)>1:
        sleep(1)
    print("check for stability")
    print("log for 15 min")
    sleep(15*60)
    
chiller.stop_control()
done=True