import time

from _hw_control import *
from loguru import logger
from run_experiment import *

from examples.BV_experiments._hw_control import command_session
from database import find_lastest_suggestion
from run_experiment import calc_gas_liquid_flow_rate, calc_inj_rate
# Initialize gryffin/Optimization

# Initialize hardware


with command_session() as sess:
    # Heater to r.t.

    # sess.put(r2_endpoint + "/temperature", params={"temperature": "21"})
    # sess.put(r2_endpoint + "/temperature", params={"temperature": "21"})
    # sess.put(r2_endpoint + "/temperature", params={"temperature": "21"})
    # sess.put(r2_endpoint + "/temperature", params={"temperature": "21"})
    # sess.put(r2_endpoint + "/power-on")

    # Start pumps with low flow rate
    sess.put(solvent_endpoint + "/infuse", params={"rate": "5 ul/min"})

    # Ensure hplc is running

    # import the condition the reaction from the database
    lasted_exp_conditions = find_lastest_suggestion()
    # example

    lasted_exp_conditions = dict(name=f"WHH-136",
                 SM_concentration=1.22,
                 time=25.0,
                 eosinY_equiv=0.01,
                 activator_equiv=0.02,
                 quencher_equiv=2.0,
                 oxygen_equiv=2.0,
                 solvent_equiv=10.0,
                 pressure=4.0,
                 temperature=30.0,
                 UV=100,
                 category=BV_description
                 )
    # calculate the parameter of loop filling
    inj_flow = calc_inj_rate(lasted_exp_conditions)
    flow_rate = calc_gas_liquid_flow_rate(lasted_exp_conditions)

    # save all running parameters and monitor data

    # run experiments
    run_experiment(inj_flow, flow_rate)

# Run optimization for MAX_TIME/comsuming all materials
# MAX_TIME = 8 * 60 * 60



# start_time = time.monotonic()

# while time.monotonic() < (start_time + MAX_TIME):
#     # query gryffin for new conditions_to_test, 1 exploration 1 exploitation (i.e. lambda 1 and -1)
#     conditions_to_test = gryffin.recommend(
#         observations=observations, num_batches=1, sampling_strategies=[-1, 1]
#     )
#
#     # evaluate the proposed parameters!
#     for conditions in conditions_to_test:
#         # Get this from your experiment!
#         conditions["product_ratio_IR"] = run_experiment(**conditions)
#
#         logger.info(f"Experiment ended: {conditions}")
#
#     observations.extend(conditions_to_test)
#     logger.info(observations)
