import time

from gryffin import Gryffin
from loguru import logger
from run_experiment import run_experiment, reactor, flowir, hexyldecanoic, socl2

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
# Heater to r.t.
reactor.put("temperature", params={"temperature": "21"})
reactor.put("power-on")

# Start pumps with low flow rate
socl2.put("flow-rate", params={"rate": "5 ul/min"})
socl2.put("infuse")

hexyldecanoic.put("flow-rate", params={"rate": "50 ul/min"})
hexyldecanoic.put("infuse")

# Ensure iCIR is running
assert (
    flowir.get("is-connected").text == "true"
), "iCIR app must be open on the control PC"
# If IR is running I just reuse previous experiment. Because cleaning the probe for the BG is slow

status = flowir.get("probe-status").text
if status == " Not running":
    # Start acquisition
    xp = {
        "template": "30sec_2days.iCIRTemplate",
        "name": "hexyldecanoic acid chlorination - automated",
    }
    flowir.put("experiment/start", xp)


# Run optimization for MAX_TIME
MAX_TIME = 8 * 60 * 60
start_time = time.monotonic()

while time.monotonic() < (start_time + MAX_TIME):
    # query gryffin for new conditions_to_test, 1 exploration 1 exploitation (i.e. lambda 1 and -1)
    conditions_to_test = gryffin.recommend(
        observations=observations,
        num_batches=1,
        sampling_strategies=[-1, 1],
    )

    # evaluate the proposed parameters!
    for conditions in conditions_to_test:
        # Get this from your experiment!
        conditions["product_ratio_IR"] = run_experiment(**conditions)

        logger.info(f"Experiment ended: {conditions}")

    observations.extend(conditions_to_test)
    logger.info(observations)
