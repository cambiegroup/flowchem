from flowchem.devices.CustomDevices.Peltier_cooler import (
    PeltierIO,
    PeltierCooler,

)
from threading import Thread
import datetime
from pathlib import Path

class PeltierDefaults:
    HEATING_PID = [0,0,0]
    COOLING_PID = [0,0,0]
    CURRENT_LIMIT_HEATING=4
    CURRENT_LIMIT_COOLING=8
    T_MAX=40
    T_MIN=-66
from time import sleep

peltier_defaults = PeltierDefaults()
peltier_port = PeltierIO("COM4")
chiller = PeltierCooler(peltier_port, peltier_defaults, address=11)

stem="ZieglerNicholslog_"
name=stem+"0"
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

start_temp = -10
end_temp = 20

chiller._set_current_limit_cooling(8)
chiller._set_current_limit_heating(4)
chiller.start_control()
for p in [4,4.1,4.2,4.3,4.4,4.5,4.6,4.7,4.8,4.9,5.1,5.2]:
    print(f"checking P for {p}")
    chiller._set_temperature(start_temp)
    chiller.set_pid_parameters(p,0,0)
    name=stem+str(p)
    print("Settling to start temp")
    while chiller.get_temperature() > start_temp + 1:
        sleep(1)
    print("Set end temp")
    chiller._set_temperature(end_temp)
    print("wait until in range")
    while chiller.get_temperature() < end_temp-1:
        sleep(1)
    print("log for 20 min")
    sleep(20*60)

start_temp = -20
end_temp = -45

chiller._set_current_limit_cooling(8)
chiller._set_current_limit_heating(4)
chiller.start_control()
for p in range(1,11):
    print(f"checking P for {p}")
    chiller._set_temperature(start_temp)
    chiller.set_pid_parameters(p,0,0)
    name=stem+"cooling"+str(p)
    print("Settling to start temp")
    while abs(abs(chiller.get_temperature()) - abs(start_temp)) > 1:
        sleep(1)
    print("Set end temp")
    chiller._set_temperature(end_temp)
    print("wait until in range")
    while abs(abs(chiller.get_temperature()) - abs(end_temp))>2:
        sleep(1)
    print("log for 20 min")
    sleep(20*60)



chiller.stop_control()
done = True

