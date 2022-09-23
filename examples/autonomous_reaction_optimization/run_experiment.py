import time
import json

import numpy as np
import pandas as pd
from scipy import integrate
from loguru import logger

from _hw_control import *


def calculate_flow_rates(SOCl2_equivalent: float, residence_time: float):
    """
    Calculate pump flow rate based on target residence time and SOCl2 equivalents

    Stream A: hexyldecanoic acid ----|
                                     |----- REACTOR ---- IR ---- waste
    Stream B: thionyl chloride   ----|

    Args:
        SOCl2_equivalent:
        residence_time:

    Returns: dict with pump names and flow rate in ml/min

    """
    REACTOR_VOLUME = 1  # ml
    HEXYLDECANOIC_ACID = 1.6  # Molar
    SOCl2 = 13  # Molar

    total_flow_rate = REACTOR_VOLUME / residence_time  # ml/min

    # Solving a system of 2 equations and 2 unknowns...
    return {
        "hexyldecanoic": (
            a := (total_flow_rate * SOCl2)
            / (HEXYLDECANOIC_ACID * SOCl2_equivalent + SOCl2)
        ),
        "socl2": total_flow_rate - a,
    }


def set_parameters(rates: dict, temperature: float):
    with command_session() as sess:
        sess.put(
            socl2_endpoint + "/flow-rate", params={"rate": f"{rates['socl2']} ml/min"}
        )
        sess.put(
            hexyldecanoic_endpoint + "/flow-rate", params={"rate": f"{rates['hexyldecanoic']} ml/min"},
        )

        # Sets heater
        heater_data = {"temperature": f"{temperature:.2f} °C"}
        sess.put(r4_endpoint + "/temperature", params=heater_data)


def wait_stable_temperature():
    """Wait until the ste temperature has been reached."""
    logger.info("Waiting for the reactor temperature to stabilize")
    with command_session() as sess:
        while True:
            r = sess.get(r4_endpoint + "/target-reached")
            if r.text == "true":
                logger.info("Stable temperature reached!")
                break
            else:
                time.sleep(5)


def get_ir_once_stable():
    """Keeps acquiring IR spectra until changes are small, then returns the spectrum."""
    logger.info("Waiting for the IR spectrum to be stable")
    with command_session() as sess:
        previous_spectrum = json.loads(sess.get(flowir_endpoint + "/sample/spectrum/last-treated").text)

    while True:
        with command_session() as sess:
            current_spectrum = json.loads(sess.get(flowir_endpoint + "/sample/spectrum/last-treated").text)

        delta = np.array(current_spectrum["intensity"]) - np.array(previous_spectrum["intensity"])
        print(f"Max delta is {delta.max()}")
        print(f"Avg delta is {delta.mean()}")

        if delta.max() < 0.01 and delta.mean() < 0.001:
            logger.info("IR spectrum stable!")
            return current_spectrum

        previous_spectrum = current_spectrum


def intagrate_peaks(ir_specturm):
    """Integrate areas from `limits.in` in the spectrum provided."""
    # List of peaks to be integrated
    peak_list = np.recfromtxt("limits.in", encoding="UTF-8")

    # Process spectrum
    df = pd.read_json(ir_specturm)
    df = df.set_index("wavenumber")

    peaks = {}
    for name, start, end in peak_list:
        # This is a common mistake since wavenumber are plot in reverse order
        if start > end:
            start, end = end, start

        df_view = df.loc[(start <= df.index) & (df.index <= end)]
        peaks[name] = integrate.trapezoid(df_view['intensity'])
        logger.debug(f"Integral of {name} between {start} and {end} is {peaks[name]}")

    # Normalize integrals
    return {k: v/sum(peaks.values()) for k, v in peaks.items()}


def run_experiment(
    SOCl2_equivalent: float, temperature: float, residence_time: float
) -> float:
    """
    Runs one experiment with the provided conditions

    Args:
        SOCl2_equivalent: SOCl2 to substrate ratio
        temperature: in Celsius
        residence_time: in minutes

    Returns: IR product area / (SM + product areas)

    """
    logger.info(f"Starting experiment with {SOCl2_equivalent:.2f} eq SOCl2, {temperature:.1f} degC and {residence_time:.2f} min")
    pump_flow_rates = calculate_flow_rates(SOCl2_equivalent, residence_time)
    set_parameters(pump_flow_rates, temperature)
    wait_stable_temperature()
    time.sleep(residence_time * 60)  # wait at least 1 residence time

    ir_spectrum = get_ir_once_stable()
    peaks = intagrate_peaks(ir_spectrum)

    return peaks["product"]
