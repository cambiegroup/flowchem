from __future__ import annotations

import copy
from typing import Tuple

import numpy as np
import opcua
import logging
from time import sleep, time

from pathlib import Path
import pandas as pd

from flowchem.devices.Hamilton.ML600 import ML600, HamiltonPumpIO
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump, KnauerValve
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.MettlerToledo.iCIR import FlowIR
from flowchem.devices.Vapourtec.R4_heater import R4Heater, VapourtecCommand
from flowchem.examples.experiments.step_one_chemometrics import measure_yield_step1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('opcua').setLevel(logging.CRITICAL)

# FILES AND PATHS
WORKING_DIR = Path().home() / "Documents"
SOURCE_FILE = WORKING_DIR / "chlorination_T_study_17_05_21.csv"
assert SOURCE_FILE.exists()
OUTPUT_FILE = WORKING_DIR / f"{SOURCE_FILE.stem}_results{SOURCE_FILE.suffix}"
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
heater = R4Heater(port="COM41")
firmware_version = heater.write_and_read_reply(VapourtecCommand.FIRMWARE)
assert "V3.68" in firmware_version
_reactor_position = 2

# loop A - 0.5 ml - filling with Elite11 pumping with ML600
# Thionyl chloride - filling
elite_pump_connection = PumpIO(port="COM5")
pump_socl2_filling = Elite11(elite_pump_connection, address=1, diameter=14.6)  # 10 mL Gastight Syringe #1010
_loopA = 0.4

# Thionyl chloride - pumping
_pump_socl2_mac = '00:80:a3:ba:bf:e2'
available_knauer_devices = autodiscover_knauer(source_ip='192.168.1.1')
pump_socl2_solvent = KnauerPump(available_knauer_devices[_pump_socl2_mac])

# Injection valve A
_valve_A_mac = '00:80:a3:ce:7e:c4'
valveA = KnauerValve(available_knauer_devices[_valve_A_mac])
valveA.switch_to_position("INJECT")  # Not necessary, used to check communication

# Injection valve B
_valve_B_mac = '00:80:a3:ce:7e:15'
valveB = KnauerValve(available_knauer_devices[_valve_B_mac])
valveB.switch_to_position("INJECT")  # This is better on inj before ML600 initialization or prevent loop contamination


# loop B - 5.0 ml - filling
# Hexyldecanoic acid - filling
ml600_acid_connection = HamiltonPumpIO(port="COM42")
pump_acid_filling = ML600(ml600_acid_connection, syringe_volume=5)
pump_acid_filling.offset_steps = 960  # Large positional offset, so that 0-loop is actually 0.1ml-loopB+0.1ml
_loopB = 4

# Hexyldecanoic acid - pumping
_pump_acid_mac = '00:20:4a:cd:b7:44'
pump_acid_solvent = KnauerPump(available_knauer_devices[_pump_acid_mac])


# Stop loop-filling pumps and start infusion pumps

# Ensure pump initializations are over
pump_acid_filling.wait_until_idle()

# Start HPLC pump
pump_acid_solvent.set_flow(0.1)
pump_acid_solvent.start_flow()
pump_socl2_solvent.set_flow(0.1)
pump_socl2_solvent.start_flow()


def calculate_flowrate(residence_time: float, equivalent: float) -> Tuple[float, float]:
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


def xp_measure_yield(max_scan: int) -> Tuple[float, float]:
    """
    Use the IR and peak fitting to measure yield.
    Keep on acquiring until CV<1% or max_scan is reached.
    """
    measured_yield = []
    while True:
        spectrum = ir_spectrometer.get_last_spectrum_treated()
        latest_yield = measure_yield_step1(spectrum.as_df())
        measured_yield.append(latest_yield)
        print(f"Acquired new spectrum -> yield is {latest_yield}!")

        # Evaluate if results are stable enough to return
        if len(measured_yield) >= 3:
            # Consider only the last 3 points
            n_yield = np.array(measured_yield[-3:])
            if n_yield.var() < 0.01 or len(measured_yield) > max_scan:
                print(f"Stop analytics! Calculated yield is {n_yield.mean()} CV {n_yield.var()} after "
                      f"{len(measured_yield)} measurements!")
                return n_yield.mean(), n_yield.var()

        last_spectrum_num = ir_spectrometer.get_sample_count()
        # Wait for new spectrum
        while ir_spectrometer.get_sample_count() == last_spectrum_num:
            sleep(1)


# Loop execute the points that are needed
logger.info("Initialization complete!")
for index, row in xp_data.iterrows():
    """
    Each cycle is an experiment, assumption is that the previous point is over.
    
    1) Set temperature
    2) Stops and reload ML600 to target
    3) Set flowrates of solvent pumps
    4) Move valves to load position
    5) Fill loops
    6) Wait for set temperature
    7) Switch valves to inject
    8) Waits 1.5 tR, start acquiring IR spectra until steady state conditions are reached or max time has passed
    9) flushes loops+reactor at higher flowrate and save results
    """
    print(f"Applying the following conditions: tR={row['tR']}, SOCl2_eq={row['eq']}, temp={row['T']}")

    # 1) Set temperature
    #  This is done first as it might take a while to equilibrate
    heater.set_temperature(channel=_reactor_position, target_temperature=row["T"], wait=False)
    logger.debug(f"Setting temperature to {row['T']}")

    # 2) Stops and reload ML600 to target
    pump_acid_filling.stop()
    pump_acid_filling.wait_until_idle()  # Wait for target reached
    pump_acid_filling.valve_position = pump_acid_filling.ValvePositionName.INPUT
    pump_acid_filling.wait_until_idle()  # Wait for target reached
    pump_acid_filling.to_volume(_loopB, speed=30)  # Refill at 10 ml/min
    pump_acid_filling.wait_until_idle()  # Wait for target reached

    # Switch to outlet
    pump_acid_filling.valve_position = pump_acid_filling.ValvePositionName.OUTPUT
    pump_acid_filling.wait_until_idle()  # Wait for target reached
    logger.debug(f"Hamilton s.pump reloaded")

    # 3) Set flowrates of solvent pumps
    _flowrate_socl2, _flowrate_acid = calculate_flowrate(row["tR"], row["eq"])
    pump_socl2_solvent.set_flow(_flowrate_socl2)
    pump_acid_solvent.set_flow(_flowrate_acid)
    logger.debug(f"Started solvent infusion at target flow rate (SOCl2={_flowrate_socl2}, acid={_flowrate_acid})")

    # 4) Move valves to load position
    valveA.switch_to_position("LOAD")
    valveB.switch_to_position("LOAD")
    logger.debug(f"Valve to load position")

    # 5) Fill loops
    pump_socl2_filling.target_volume = _loopA + 0.05
    pump_socl2_filling.infusion_rate = 1
    pump_socl2_filling.run()
    pump_acid_filling.to_volume(volume_in_ml=0, speed=30)
    # Wait for filling complete
    pump_socl2_filling.wait_until_idle()
    pump_acid_filling.wait_until_idle()
    logger.debug(f"Loops filled!")

    # 6) Wait for set temperature
    heater.wait_for_target_temp(channel=_reactor_position)
    logger.debug(f"Target temperature reached")

    # 7) Switch valves to inject
    sleep(3)  # Ensure filling is complete
    valveB.switch_to_position("INJECT")
    valveA.switch_to_position("INJECT")
    logger.info(f"Experiment started!")
    start_time = time()

    # 8) Waits 2 tR, and measure yield and save
    sleep(60 * row["tR"] * 2)
    logger.debug(f"Reached 2 tR")

    # Max 1.5 tR time to measure yield, integration is 15" so 4 scans per minute
    max_scan = row["tR"] * 4 * 1.5
    result_row = copy.deepcopy(row)
    result_row["yield"], result_row["cv"] = xp_measure_yield(max_scan)
    logger.info(f"Yield obtained: {result_row['yield']}")

    # Write result to file
    results = pd.DataFrame(columns=list(result_row.keys()))
    results = results.append(result_row)

    # Append to existing file, header written only the first time
    results.to_csv(OUTPUT_FILE, mode='a', header=not OUTPUT_FILE.exists())
    logger.debug(f"Updated results in {OUTPUT_FILE}")

    # 9) flushes loops+reactor at higher flowrate
    # For the flushes reach 5 reactor volumes.
    current_time = time()
    reactor_volumes_infused = (current_time - start_time) / (row["tR"] * 60)
    reactor_volumes_to_flush = 5 - reactor_volumes_infused
    # Now let's flush the remaining reactor volume with the flowrate of 1min tR
    _fast_flowrate_socl2, _fast_flowrate_acid = calculate_flowrate(1, row["eq"])  # Flush flowrate is tR=1
    pump_socl2_solvent.set_flow(_flowrate_socl2)
    pump_acid_solvent.set_flow(_fast_flowrate_acid)
    logger.debug(f"Waiting {reactor_volumes_to_flush} reactor volume for the reaction to leave the reactor.")
    sleep(reactor_volumes_to_flush*60)

    # Once experiment is performed remove it from the source CSV
    xp_data.drop(index, inplace=True)
    xp_data.to_csv(SOURCE_FILE)
    logger.info(f"XP completed!")

# Stop all
pump_acid_filling.stop()
pump_socl2_filling.stop()
pump_socl2_solvent.stop_flow()
pump_acid_solvent.stop_flow()