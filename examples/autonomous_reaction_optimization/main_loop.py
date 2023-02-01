import time

from gryffin import Gryffin
from loguru import logger
from run_experiment import run_experiment

from examples.autonomous_reaction_optimization._hw_control import (
    command_session,
    socl2_endpoint,
    r4_endpoint,
    hexyldecanoic_endpoint,
    flowir_endpoint,
)

logger.add("./xp.log", level="INFO")

# load config
config = {
    "parameters": [
        {"name": "SOCl2_equivalent", "type": "continuous", "low": 1.0, "high": 1.5},
        {"name": "temperature", "type": "continuous", "low": 30, "high": 65},
        {"name": "residence_time", "type": "continuous", "low": 2, "high": 20},
    ],
    "objectives": [
        {"name": "product_ratio_IR", "goal": "max"},
    ],
}

# Initialize gryffin
gryffin = Gryffin(config_dict=config)
observations = []


# Initialize hardware
with command_session() as sess:
    # Heater to r.t.
    sess.put(r4_endpoint + "/temperature", params={"temperature": "21"})
    sess.put(r4_endpoint + "/power-on")

    # Start pumps with low flow rate
    sess.put(socl2_endpoint + "/flow-rate", params={"rate": "5 ul/min"})
    sess.put(socl2_endpoint + "/infuse")

    sess.put(hexyldecanoic_endpoint + "/flow-rate", params={"rate": "50 ul/min"})
    sess.put(hexyldecanoic_endpoint + "/infuse")

    # Ensure iCIR is running
    assert (
        sess.get(flowir_endpoint + "/is-connected").text == "true"
    ), "iCIR app must be open on the control PC"
    # If IR is running I just reuse previous experiment. Because cleaning the probe for the BG is slow
    status = sess.get(flowir_endpoint + "/probe-status")
    if status == " Not running":
        # Start acquisition
        xp = {
            "template": "30sec_2days.iCIRTemplate",
            "name": "hexyldecanoic acid chlorination - automated",
        }
        sess.put(flowir_endpoint + "/experiment/start", params=xp)


# Run optimization for MAX_TIME
MAX_TIME = 8 * 60 * 60
start_time = time.monotonic()

while time.monotonic() < (start_time + MAX_TIME):
    # query gryffin for new conditions_to_test, 1 exploration 1 exploitation (i.e. lambda 1 and -1)
    conditions_to_test = gryffin.recommend(
        observations=observations, num_batches=1, sampling_strategies=[-1, 1]
    )

    # evaluate the proposed parameters!
    for conditions in conditions_to_test:
        # Get this from your experiment!
        conditions["product_ratio_IR"] = run_experiment(**conditions)

        logger.info(f"Experiment ended: {conditions}")

    observations.extend(conditions_to_test)
    logger.info(observations)
