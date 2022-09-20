import time

from gryffin import Gryffin
from run_experiment import run_experiment

# load config
config = {
    "parameters": [
        {"name": "SOCl2_equivalent", "type": "continuous", "low": 1.0, "high": 1.5},
        {"name": "temperature", "type": "continuous", "low": 20, "high": 100},
        {"name": "residence_time", "type": "continuous", "low": 1, "high": 60},
    ],
    "objectives": [
        {"name": "product_ratio_IR", "goal": "max"},
    ],
}

# Initialize gryffin
gryffin = Gryffin(config_dict=config)
observations = []

# Initialize hardware
# TODO start

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

    observations.extend(conditions_to_test)
