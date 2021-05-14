from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
import opcua
import logging
from flowchem.devices.MettlerToledo.iCIR import FlowIR
import pandas as pd
from time import sleep, time, asctime, localtime

from pathlib import Path

# Temperature control is not automated yet
CURRENT_TEMPERATURE = 30

WORKING_DIR = Path().home() / "Documents"

SOURCE_FILE = WORKING_DIR / "chlorination_14_05_21.csv"
assert SOURCE_FILE.exists()

Path(WORKING_DIR / "spectra").mkdir(exist_ok=True)  # Also we will need to save stuff in this folder

# Load xp data to run
xp_data = pd.read_csv(SOURCE_FILE)
xp_data.query(f"T == {CURRENT_TEMPERATURE}", inplace=True)
if xp_to_run := len(xp_data.index) > 0:
    print(f"{xp_to_run} points left to run at the current temperature (i.e. {CURRENT_TEMPERATURE})")
else:
    raise RuntimeError(f"No points left to run at {CURRENT_TEMPERATURE} in this experiment!")


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("flowchem")


# def are_pumps_moving(column, row):
    # # check if any pump stalled, if so, set the bool false, else true
    # if pump_hexdiol.is_moving() and pump_hexyldecanoic_acid_chloride.is_moving():
    #     conditions_results.at[row, column] = "Success"
    #     conditions_results.to_csv(WORKING_DIR.joinpath(OUTPUT_FILE))
    #     return True
    # else:
    #     conditions_results.at[row, column] = "Failed"
    #     conditions_results.to_csv(WORKING_DIR.joinpath(OUTPUT_FILE))
    #     return False


# Hardware
# IR
ir_spectrometer = FlowIR(opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS))
if not ir_spectrometer.is_iCIR_connected:
    raise RuntimeError("FlowIR not connected :(")

# Thionyl chloride pump
pump_connection = PumpIO('COM5')
pump_socl2 = Elite11(pump_connection, diameter=16.4)
# Start pump
pump_socl2.stop()
pump_socl2.infusion_rate = 0.001
pump_socl2.infuse_run()

# Acid pump




