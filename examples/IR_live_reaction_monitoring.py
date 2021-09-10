import datetime
import pandas as pd
import asyncio
from lmfit.models import PseudoVoigtModel, LinearModel

import matplotlib.pyplot as plt
from asyncua import Client
from matplotlib import style

from flowchem.devices.MettlerToledo.iCIR_async import FlowIR

live_results = pd.DataFrame()

# create the fitting parameters
peak_chloride = PseudoVoigtModel(prefix="chloride_")
peak_dimer = PseudoVoigtModel(prefix="dimer_")
peak_monomer = PseudoVoigtModel(prefix="monomer_")
offset = LinearModel()
model = peak_chloride + peak_dimer + peak_monomer + offset

pars = model.make_params()
pars["chloride_center"].set(value=1800, min=1790, max=1810)
pars["chloride_amplitude"].set(min=0)  # Positive peak
pars["chloride_sigma"].set(min=5, max=50)  # Set full width half maximum

pars["dimer_center"].set(value=1715, min=1706, max=1716)
pars["dimer_amplitude"].set(min=0)  # Positive peak
pars["dimer_sigma"].set(min=1, max=15)  # Set full width half maximum

pars["monomer_center"].set(value=1740, min=1734, max=1752)
pars["monomer_amplitude"].set(min=0)  # Positive peak
pars["monomer_sigma"].set(min=4, max=30)  # Set full width half maximum


def calculate_yield(spectrum_df):
    spectrum_df.query(f"{1600} <= index <= {1900}", inplace=True)
    x_arr = spectrum_df.index.to_numpy()
    y_arr = spectrum_df[0]

    result = model.fit(y_arr, pars, x=x_arr)
    product = result.values["chloride_amplitude"]
    sm = result.values["dimer_amplitude"] + result.values["monomer_amplitude"]
    latest_yield = product / (sm + product)
    return latest_yield


# PLOT SETUP
style.use("seaborn-dark")
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
reaction_time = []
reaction_yield = []


async def get_data():
    async with Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS, timeout=3600) as opcua_client:
        ir_spectrometer = FlowIR(opcua_client)
        # await ir_spectrometer.check_version()
        #
        # if await ir_spectrometer.is_iCIR_connected:
        #     print(f"FlowIR connected!")
        # else:
        #     print("FlowIR not connected :(")
        #     import sys
        #     sys.exit()
        #
        # template_name = "15_sec_integration.iCIRTemplate"
        # await ir_spectrometer.start_experiment(name="reaction_monitoring", template=template_name)
        #
        # spectrum = await ir_spectrometer.get_last_spectrum_treated()
        # while spectrum.empty:
        #     spectrum = await ir_spectrometer.get_last_spectrum_treated()

        # This will become a while true
        while True:
            spectra_count = await ir_spectrometer.get_sample_count()
            while await ir_spectrometer.get_sample_count() == spectra_count:
                await asyncio.sleep(1)

            spectrum = await ir_spectrometer.get_last_spectrum_treated()
            # Restrict ROI to 1900 - 1600 cm-1
            spectrum_df = spectrum.as_df()
            latest_yield = calculate_yield(spectrum_df)
            print(f"yield is {latest_yield}")
            reaction_time.append(datetime.datetime.now())
            reaction_yield.append(latest_yield)

        await ir_spectrometer.stop_experiment()


async def plot_data():
    while True:
        # ax1.clear()
        # ax1.plot(reaction_time, reaction_yield)
        # plt.pause(0.01)
        await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.create_task(get_data())
loop.create_task(plot_data())
loop.run_forever()
