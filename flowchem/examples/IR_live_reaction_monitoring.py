import datetime

import pandas as pd
import asyncio
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from asyncua import Client
from matplotlib import style

from flowchem.devices.MettlerToledo.iCIR_async import FlowIR

live_results = pd.DataFrame()

# PLOT SETUP
style.use("seaborn-dark")
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
reaction_time = []
reaction_yield = []
# Add first point
reaction_time.append(datetime.datetime.now())
reaction_yield.append(0.0)


async def get_data():
    async with Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS) as opcua_client:
        ir_spectrometer = FlowIR(opcua_client)
        await ir_spectrometer.check_version()

        if await ir_spectrometer.is_iCIR_connected:
            print(f"FlowIR connected!")
        else:
            print("FlowIR not connected :(")
            import sys
            sys.exit()

        template_name = "15_sec_integration.iCIRTemplate"
        await ir_spectrometer.start_experiment(name="reaction_monitoring", template=template_name)

        spectrum = await ir_spectrometer.get_last_spectrum_treated()
        while spectrum.empty:
            spectrum = await ir_spectrometer.get_last_spectrum_treated()

        # This will become a while true
        while True:
            spectra_count = await ir_spectrometer.get_sample_count()
            while await ir_spectrometer.get_sample_count() == spectra_count:
                await asyncio.sleep(1)

            spectrum = await ir_spectrometer.get_last_spectrum_treated()
            chloride = spectrum.integrate(1765, 1840)
            acid = spectrum.integrate(1710, 1765)
            latest_yield = chloride/(chloride + acid)
            print(f"yield is {latest_yield}")
            reaction_time.append(datetime.datetime.now())
            reaction_yield.append(latest_yield)

        await ir_spectrometer.stop_experiment()


async def plot_data():
    while True:
        ax1.clear()
        ax1.plot(reaction_time, reaction_yield)
        plt.pause(0.01)
        await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.create_task(get_data())
loop.create_task(plot_data())
loop.run_forever()
