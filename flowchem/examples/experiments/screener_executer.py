import opcua
import logging
from time import sleep, time, asctime, localtime

from pathlib import Path
import pandas as pd

from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.MettlerToledo.iCIR import FlowIR

# Temperature control is not automated yet
CURRENT_TEMPERATURE = 30

WORKING_DIR = Path().home() / "Documents"

SOURCE_FILE = WORKING_DIR / "chlorination_14_05_21.csv"
assert SOURCE_FILE.exists()

Path(WORKING_DIR / "spectra").mkdir(exist_ok=True)  # Also we will need to save stuff in this folder

# Load xp data to run
source_df = pd.read_csv(SOURCE_FILE, index_col=0)
xp_data = source_df.query(f"T == {CURRENT_TEMPERATURE}", inplace=False)
if (xp_to_run := len(xp_data)) > 0:
    print(f"{xp_to_run} points left to run at the current temperature (i.e. {CURRENT_TEMPERATURE})")
else:
    raise RuntimeError(f"No points left to run at {CURRENT_TEMPERATURE} in this experiment!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flowchem")

# Hardware
# IR
ir_spectrometer = FlowIR(opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS))
if not ir_spectrometer.is_iCIR_connected:
    raise RuntimeError("FlowIR not connected :(")

# Thionyl chloride pump
pump_connection = PumpIO('COM5')
pump_socl2 = Elite11(pump_connection, address=1, diameter=16.4)

# Acid pump
_pump_acid_mac = '00:20:4a:cd:b7:44'
available_knauer_devices = autodiscover_knauer(source_ip='192.168.1.1')
try:
    pump_acid = KnauerPump(available_knauer_devices[_pump_acid_mac])
except KeyError as e:
    raise RuntimeError("Acid pump unreachable. Is it connected and powered on?") from e

# Start pumps
pump_socl2.stop()
pump_socl2.infusion_rate = 0.01
pump_socl2.infuse_run()

pump_acid.set_flow(0.1)
pump_acid.start_flow()


def remove_xp_from_source_df(index_to_remove):
    source_df.drop(index_to_remove, inplace=True)
    source_df.to_csv(SOURCE_FILE)


# Loop execute the points that are needed
for index, row in xp_data.iterrows():
    print(f"Applying the follwoiung conditions: tR={row['tR']}, SOCl2_eq={row['eq']}, temp={row['T']}")

    # Once experiment is performed remove it from the source CSV
    #remove_xp_from_source_df(index_to_remove=index)
