from __future__ import annotations

import opcua
import logging
from time import sleep, time, asctime, localtime

from pathlib import Path
import pandas as pd

from flowchem.devices.Hamilton.ML600 import ML600, HamiltonPumpIO
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump, KnauerValve
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.MettlerToledo.iCIR import FlowIR
from flowchem.devices.Vapourtec.R4_heater import R4Heater, VapourtecCommand

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flowchem")

# FILES AND PATHS
WORKING_DIR = Path().home() / "Documents"
SOURCE_FILE = WORKING_DIR / "chlorination_14_05_21.csv"
assert SOURCE_FILE.exists()
# Ensure spectra folder exits
Path(WORKING_DIR / "spectra").mkdir(exist_ok=True)

# Load xp data to run
xp_data = pd.read_csv(SOURCE_FILE, index_col=0)
assert len(xp_data) > 0, "No experiments left to run! What am I supposed to do ? ;)"

REACTOR_VOLUME = 1.0

# Analytics - IR
ir_spectrometer = FlowIR(opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS))
if not ir_spectrometer.is_iCIR_connected:
    raise RuntimeError("FlowIR not connected :(")

# Heater - R4
heater = R4Heater(port=11)
firmware_version = heater.write_and_read_reply(VapourtecCommand.FIRMWARE)
assert "V3.68" in firmware_version
_reactor_position = 0

# loop A - 0.5 ml - filling with Elite11 pumping with ML600
# Thionyl chloride - filling
elite_pump_connection = PumpIO('COM5')
pump_socl2_filling = Elite11(elite_pump_connection, address=1, diameter=14.6)  # 10 mL Gastight Syringe Model 1010 TLL, PTFE Luer Lock
_loopA = 0.5

# Thionyl chloride - pumping
ml600_socl2_connection = HamiltonPumpIO(port="COM7")
pump_socl2_solvent = ML600(ml600_socl2_connection, syringe_volume=5)

# loop B - 5.0 ml - filling
# Hexyldecanoic acid - filling
ml600_acid_connection = HamiltonPumpIO(port="COM8")
pump_acid_filling = ML600(ml600_acid_connection, syringe_volume=5)
pump_acid_filling.offset_steps = 960  # Large positional offset, so that 0-loop is actually 0.1ml-loopB+0.1ml
_loopB = 5

# Hexyldecanoic acid - pumping
_pump_acid_mac = '00:20:4a:cd:b7:44'
available_knauer_devices = autodiscover_knauer(source_ip='192.168.1.1')
try:
    pump_acid_solvent = KnauerPump(available_knauer_devices[_pump_acid_mac])
except KeyError as e:
    raise RuntimeError("Acid pump unreachable. Is it connected and powered on?") from e

# Injection valve A
_valve_A_mac = '00:80:a3:ce:7e:c4'
valveA = KnauerValve(available_knauer_devices[_valve_A_mac])
valveA.switch_to_position("LOAD")  # Not necessary, used to check communication

# Injection valve B
_valve_B_mac = '00:80:a3:ce:8e:47'
valveB = KnauerValve(available_knauer_devices[_valve_B_mac])
valveB.switch_to_position("LOAD")  # Not necessary, used to check communication

# Stop loop-filling pumps and start infusion pumps

# Start infusion pumps
# Thionyl chloride - filling
pump_socl2_filling.stop()
pump_socl2_filling.infusion_rate = 0.01
pump_socl2_filling.infuse_run()

pump_acid_solvent.set_flow(0.1)
pump_acid_solvent.start_flow()


def calculate_flowrate(residence_time: float, equivalent: float) -> tuple[float, float]:
    """
    Given residence time, equivalent returns flowrate.
    Reactor volume is from global REACTOR_VOLUME, stock solution concentration are such that acid is 1/10 SOCl2.
    """
    total_flow = REACTOR_VOLUME / residence_time
    # 0.1 is the concentration ratio, so...
    ratio_socl2 = equivalent * 0.1
    # flow_socl2 = flow_acid * ratio_socl2
    # flow_socl2 + flow_acid = total_flow
    # Hence...
    flow_socl2 = (total_flow * ratio_socl2) / (1+ratio_socl2)
    flow_acid = total_flow - flow_socl2
    return flow_socl2, flow_acid


# Loop execute the points that are needed
for index, row in xp_data.iterrows():
    """
    Each cycle is an experiment, assumption is that the previous point is over.
    
    1) Set temperature (done first as it might take a while to equilibrate)
    2) stops and reload both ML600 if necessary    
    3) Set flowrates of solvent pumps to match target residence time
    4) Move valves in load positions
    5) Fill loops
    6) Verify that the target temperature has been reached
    7) Switch both valves to INJECT
    8) Waits 1.5 tR, and measure yield and save
    9) flushes loops+reactor at higher flowrate and save results
    """
    print(f"Applying the following conditions: tR={row['tR']}, SOCl2_eq={row['eq']}, temp={row['T']}")

    # 1) Set temperature
    heater.set_temperature(channel=_reactor_position, target_temperature=row["T"], wait=False)

    # 2) Stops and reload ML600 to target
    pump_socl2_solvent.stop()
    pump_socl2_solvent.valve_position = pump_socl2_solvent.ValvePositionName.INPUT
    pump_socl2_solvent.to_volume(5.0, speed=60)  # Refill at 5 ml/min

    pump_acid_filling.stop()
    pump_acid_filling.valve_position = pump_acid_filling.ValvePositionName.INPUT
    pump_acid_filling.to_volume(_loopB, speed=60)  # Refill at 5 ml/min

    # Wait for target reached
    pump_socl2_solvent.wait_until_idle()
    pump_acid_filling.wait_until_idle()

    # Switch to outlet
    pump_socl2_solvent.valve_position = pump_socl2_solvent.ValvePositionName.OUTPUT
    pump_acid_filling.valve_position = pump_acid_filling.ValvePositionName.OUTPUT

    # 3) Set flowrate of solvent pumps
    _flowrate_socl2, _flowrate_acid = calculate_flowrate(row["tR"], row["eq"])
    pump_socl2_solvent.to_volume(0, speed=pump_socl2_solvent.flowrate_to_seconds_per_stroke(_flowrate_socl2))
    pump_acid_solvent.set_flow(_flowrate_acid)

    # 4) Move valves to load
    valveA.switch_to_position("LOAD")
    valveB.switch_to_position("LOAD")

    # 5) Fill loops
    pump_socl2_filling.target_volume = _loopA
    pump_socl2_filling.infusion_rate = 1
    pump_socl2_filling.infuse_run()
    pump_acid_filling.to_volume(volume_in_ml=0, speed=30)
    pump_socl2_filling.wait_until_idle()
    pump_acid_filling.wait_until_idle()

    # 6) Wait for temperature
    heater.wait_for_target_temp(channel=_reactor_position)

    # 7) Switch valves to inject
    valveA.switch_to_position("INJECT")
    valveB.switch_to_position("INJECT")
    print("XP started! :)")
    start_time = time()

    # 8) Waits 1.5 tR, and measure yield and save
    sleep(60 * row["tR"] * 1.5)
    # DO IR STUFF
    # Start acquiring IR spectra until steady state conditions are reached or max time has passed


    # 9) flushes loops+reactor at higher flowrate
    # For the flushes reach 8 reactor volumes.
    current_time = time()
    reactor_volumes_infused = current_time - start_time / (row["tR"] * 60)
    reactor_volumes_to_flush = 8 - reactor_volumes_infused
    # Now let's flush the remaining reactor volume with the flowrate of 1min tR
    _fast_flowrate_socl2, _fast_flowrate_acid = calculate_flowrate(1, row["eq"])  # Flush flowrate is tR=1
    pump_socl2_solvent.to_volume(0, speed=pump_socl2_solvent.flowrate_to_seconds_per_stroke(_flowrate_socl2))
    pump_acid_solvent.set_flow(_fast_flowrate_acid)
    sleep(reactor_volumes_to_flush*60)

    # Given that the loop hosts 5.5 reactor volumes, and at least 1.5 have already been waited for, just flash 4 VR
    pump_socl2_solvent

pump_acid_filling.stop()
pump_socl2_filling.stop()


    # Once experiment is performed remove it from the source CSV
    # source_df.drop(index, inplace=True)
    # source_df.to_csv(SOURCE_FILE)
