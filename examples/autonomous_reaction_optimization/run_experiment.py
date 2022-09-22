import random
import time

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
    with command_session() as sess:
        while True:
            r = sess.get(r4_endpoint + "/target-reached")
            if r.text == "true":
                break
            else:
                time.sleep(5)


def get_ir_once_stable():
    """Keeps acquiring IR spectra until changes are small, then returns the spectrum."""
    with command_session() as sess:
        # Get IR, check previous, return average when stable
        pass


def calculate_peak_ratio(ir_spectrum):
    """Given the IR spectrum returns the product area / total area ratio."""
    return random.random()


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
    pump_flow_rates = calculate_flow_rates(SOCl2_equivalent, residence_time)
    set_parameters(pump_flow_rates, temperature)
    wait_stable_temperature()
    time.sleep(residence_time * 60)  # wait at least 1 residence time

    ir_spectrum = get_ir_once_stable()

    return calculate_peak_ratio(ir_spectrum)
