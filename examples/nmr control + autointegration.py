import asyncio
import glob
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import itertools as it
from flowchem.components.devices.Magritek import Spinsolve, NMRSpectrum
from flowchem import Knauer16PortValve


Collector_DELAY = 60 * 30  # in sec
START_POSITION = 7  # First position for collection


async def Collector():
    valve = Knauer16PortValve(ip_address="192.168.1.122")
    await valve.initialize()

    position = START_POSITION

    while True:
        await valve.switch_to_position(str(position))
        await asyncio.sleep(Collector_DELAY)
        position += 1
        if position > 16:
            position = 1


NMR_DELAY = 60 * 2  # in sec
counter = it.count()

# read in the integration limits
peak_list = np.recfromtxt("limits.in", encoding="UTF-8")
NMR_forlder_month = r"C:\Projects\Data\2022\03"


async def Analysis(observed_result):
    nmr = Spinsolve(host="BSMC-YMEF002121")

    while True:
        path = await nmr.run_protocol(
            "1D FLUORINE+",
            {
                "Number": 128,
                "AcquisitionTime": 3.2,
                "RepetitionTime": 2,
                "PulseAngle": 90,
            },
        )
        observed_time = (NMR_DELAY / 60 + 4) * next(counter)
        if str(path) == ".":
            # continue
            dir_list_day = os.listdir(NMR_forlder_month)
            dir_list_time = os.listdir(NMR_forlder_month / Path(dir_list_day[-1]))
            path = NMR_forlder_month / Path(dir_list_day[-1]) / Path(dir_list_time[-1])
            print(path)

        # else:
        peak_normalized_list = peak_aquire_process(path)
        observed_result = observed_result.append(
            pd.DataFrame(
                peak_normalized_list,
                index=["SM", "product", "side-P"],
                columns=[observed_time],
            ).T
        )

        # result
        print(observed_result)
        # save
        observed_result.to_csv(
            r"W:\BS-FlowChemistry\People\Wei-Hsin\Spinsolve\export_dataframe_0317_03.csv",
            header=True,
        )
        plt.figure()
        observed_result.plot()
        plt.legend(loc="best")
        plt.savefig(
            r"W:\BS-FlowChemistry\People\Wei-Hsin\Spinsolve\export_plot_0317_03.png"
        )

        await asyncio.sleep(NMR_DELAY)


def peak_aquire_process(path):
    spectrum = NMRSpectrum(path)
    spectrum.process()

    peak_sum_list = []

    # loop over the integration limits
    for name, start, end in peak_list:
        min = spectrum.uc(start, "ppm")
        max = spectrum.uc(end, "ppm")
        if min > max:
            min, max = max, min
        # extract the peak
        peak = spectrum.processed_data[min : max + 1]
        peak_sum_list.append(peak.sum())

    # peak normalization
    y = sum(peak_sum_list)
    peak_normalized_list = [i / y for i in peak_sum_list]
    return peak_normalized_list


async def main():
    observed_time = 0
    observed_result = pd.DataFrame(
        [1, 0, 0], index=["SM", "product", "side-P"], columns=[observed_time]
    ).T
    await asyncio.wait([Collector(), Analysis(observed_result)])
    # await asyncio.gather([Collector(),Analysis(observed_result)])

    # await Analysis(observed_result)
    # await Collector()


if __name__ == "__main__":
    asyncio.run(main())
