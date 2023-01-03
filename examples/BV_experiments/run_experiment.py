import time

import numpy as np
import pandas as pd
from _hw_control import *
from loguru import logger
from scipy import integrate

from collections import namedtuple


def calculate_for_injection_loop(Equiv_dict: dict)-> list:
    """
    Calculate the time and the

    pump0: EosinY ---|



    Args:
        Equiv_dict: the equivalent of substrates (in mole)
        total_infusion_rate: the speed of filling the loop, default 0.02 ml/min

    Returns:dict with pump name/address and flow rate in uL/min

    """
    LOOP_VOLUME = 0.1  # ml
    FILLING_TIME = 5  # min
    total_infusion_rate = LOOP_VOLUME / FILLING_TIME  # 0.02  ml/min
    FIRST_MIX_TUBE = 0.0106  # ml
    SECOND_MIX_TUBE = 0.0212  # mL

    # EY: 0.05M, Boric acid: 1.00M in methanol
    # SUB ={SM :{"MW":146.19, "density":1.230}, Tol :{"MW":92.14, "density":0.866}, DIEPA :{"MW":129.25, "density":0.742}}

    # Calculate the required volume to fill the loop
    vol_dict = {
        "SMIS": 0.225, "EY": Equiv_dict["EY"] * 20, "Activator": Equiv_dict["H3BO3"] * 1,
        "Quencher": Equiv_dict["DIPEA"] * 0.174, "Solvent": 0
    }
    flow_unit = total_infusion_rate / sum(vol_dict.values())
    # Infuse flow rate
    logger.debug((dict((s, str(vol_dict[s] * flow_unit) + " ml/min") for s in vol_dict)))

    # Calculate the time period (in min) of filling
    frac_vol_list = [FIRST_MIX_TUBE+SECOND_MIX_TUBE * 0.5, LOOP_VOLUME * 1.1, FIRST_MIX_TUBE+SECOND_MIX_TUBE * 0.75, (FIRST_MIX_TUBE+SECOND_MIX_TUBE) * 3]
    frac_speed_list = [flow_unit * (vol_dict["EY"] + vol_dict["Activator"]), total_infusion_rate, total_infusion_rate, total_infusion_rate * 1.5]
    frac_time_list = [v/s for v,s in zip(frac_vol_list, frac_speed_list)]

    return


def calculate_injection_loop(SOCl2_equivalent: float, residence_time: float):
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
    REACTOR_VOLUME = 10  # ml
    HEXYLDECANOIC_ACID = 1.374  # Molar
    SOCl2 = 13.768  # Molar

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
            hexyldecanoic_endpoint + "/flow-rate",
            params={"rate": f"{rates['hexyldecanoic']} ml/min"},
        )

        # Sets heater
        heater_data = {"temperature": f"{temperature:.2f} °C"}
        sess.put(r4_endpoint + "/temperature", params=heater_data)


def wait_stable_temperature():
    """Wait until the ste temperature has been reached."""
    logger.info("Waiting for the reactor temperature to stabilize")
    while True:
        with command_session() as sess:
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
        # Wait for first spectrum to be available
        while int(sess.get(flowir_endpoint + "/sample-count").text) == 0:
            time.sleep(1)
        # Get spectrum
        previous_spectrum = pd.read_json(
            sess.get(flowir_endpoint + "/sample/spectrum-treated").text
        )
        previous_spectrum = previous_spectrum.set_index("wavenumber")
        # In case the id has changed between requests (highly unlikely)
        last_sample_id = int(sess.get(flowir_endpoint + "/sample-count").text)

    while True:
        # Wait for a new spectrum
        while True:
            with command_session() as sess:
                current_sample_id = int(
                    sess.get(flowir_endpoint + "/sample-count").text
                )
            if current_sample_id > last_sample_id:
                break
            else:
                time.sleep(2)

        with command_session() as sess:
            current_spectrum = pd.read_json(
                sess.get(flowir_endpoint + "/sample/spectrum-treated").text
            )
            current_spectrum = current_spectrum.set_index("wavenumber")

        previous_peaks = integrate_peaks(previous_spectrum)
        current_peaks = integrate_peaks(current_spectrum)

        delta_product_ratio = abs(current_peaks["product"] - previous_peaks["product"])
        logger.info(f"Current product ratio is {current_peaks['product']}")
        logger.debug(f"Delta product ratio is {delta_product_ratio}")

        if delta_product_ratio < 0.002:  # 0.2% error on ratio
            logger.info("IR spectrum stable!")
            return current_peaks

        previous_spectrum = current_spectrum
        last_sample_id = current_sample_id


def integrate_peaks(ir_spectrum):
    """Integrate areas from `limits.in` in the spectrum provided."""
    # List of peaks to be integrated
    peak_list = np.recfromtxt("limits.in", encoding="UTF-8")

    peaks = {}
    for name, start, end in peak_list:
        # This is a common mistake since wavenumber are plot in reverse order
        if start > end:
            start, end = end, start

        df_view = ir_spectrum.loc[
            (start <= ir_spectrum.index) & (ir_spectrum.index <= end)
            ]
        peaks[name] = integrate.trapezoid(df_view["intensity"])
        logger.debug(f"Integral of {name} between {start} and {end} is {peaks[name]}")

    # Normalize integrals

    return {k: v / sum(peaks.values()) for k, v in peaks.items()}


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
    logger.info(
        f"Starting experiment with {SOCl2_equivalent:.2f} eq SOCl2, {temperature:.1f} degC and {residence_time:.2f} min"
    )
    # Set stand-by flow-rate first
    set_parameters({"hexyldecanoic": "0.1 ml/min", "socl2": "10 ul/min"}, temperature)
    wait_stable_temperature()
    # Set actual flow rate once the set temperature has been reached
    pump_flow_rates = calculate_flow_rates(SOCl2_equivalent, residence_time)
    set_parameters(pump_flow_rates, temperature)
    # Wait 1 residence time
    time.sleep(residence_time * 60)
    # Start monitoring IR
    peaks = get_ir_once_stable()

    return peaks["product"]


if __name__ == "__main__":
    print(get_ir_once_stable())
