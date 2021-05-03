# ToDo
#  A)  for experiment:
#  OK 1) Create reasonable boundary conditions -> from experiment
#  OK 2) equivalents  and residence time are the x and y axis, yield the z.  Flow rates follow from residence time and equivalents
#  OK 3) within these, create a matrix with a reasonable number of points  -> 9 * 10? 1, 1.1, 1.2 - 1.9, 1-10 min. flowrate = Ivol / Rtime. from this, individual flow rates follow
#  OK 4) Iterate through these points, being the conditions for the experiment and do this 2 times, in orthogonal direction
#  B) for hardware and control
#  OK 1) make sure that the syringes don't stall/empty with keepalive
#  OK 2) set  flow rate for first point
#  OK 3) start syringes once
#  OK 4) wait for equilibration
#  5) measure spectra and calculate yield. repeat that 3 times
#  C) Inputs and outputs should be:
#  OK 1) a dictionary, also check what was used in the sugar optimizer, probably bendable. Go for pandas data frame
#  OK kind of 2) output needs to be condition and yield. Simply append yield to empty field in data frame?

from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
import numpy as np
import pandas as pd
from time import sleep

# hard parameters
reactor_volume = 2

def flow_rates(volume, residence_time, equivalents):
    total_flow = volume/residence_time
    # 0.1 is the concentration ratio
    flow_thio = total_flow*0.1*equivalents
    flow_acid = total_flow-flow_thio
    return round(flow_thio, 3), round(flow_acid, 3)


# prepare the IO Frame
equivalents = np.arange(start=1, stop=2.1, step=0.1)
residence_times = np.arange(start=1, stop=11)

conditions_results = pd.DataFrame(columns=['residence_time', 'eq_thio','flow_thio', 'flow_acid', 'yield_1', 'yield_2', 'yield_3', 'yield_1_rev', 'yield_2_rev', 'yield_3_rev', 'Run_forward', 'Run_backward'])

aa = []
bb = []
for residence_time in residence_times:
    for equivalent in equivalents:
        aa.append(residence_time)
        bb.append(equivalent)

conditions_results['residence_time']=aa
conditions_results['eq_thio']=bb

# now, iterate through the dataframe and calculate flow rates
for ind in conditions_results.index:
    conditions_results.at[ind, 'flow_thio'], conditions_results.at[ind, 'flow_acid'] = flow_rates(reactor_volume, conditions_results.at[ind, 'residence_time'] , conditions_results.at[ind, 'eq_thio'])


# Hardware
pump_connection = PumpIO('COM5')

pump_thionyl_chloride = Elite11(pump_connection, address=0)
pump_hexyldecanoic_acid = Elite11(pump_connection, address=1)



# Dataframe already is in the right order, now iterate through from top and from bottom, run the experiments and set the boolean
# assume that the correct syringe diameter was manually set
for ind in conditions_results.index:
    if not conditions_results.at[ind, 'Run_forward']:
        # also check the bool, if it ran already, don't rerun it. but skip it
        pump_thionyl_chloride.infusion_rate = conditions_results.at[ind, 'flow_thio']
        pump_hexyldecanoic_acid.infusion_rate = conditions_results.at[ind, 'flow_acid']
        if pump_thionyl_chloride.is_moving() and pump_hexyldecanoic_acid.is_moving():
            pass
        else:
            pump_thionyl_chloride.infuse_run()
            pump_hexyldecanoic_acid.infuse_run()

        # wait until several reactor volumes are through
        sleep(3*conditions_results.at[ind, 'residence_time'])

        # check if any pump stalled, if so, set the bool false, leave loop
        if pump_thionyl_chloride.is_moving() and pump_hexyldecanoic_acid.is_moving():
            pass
        else:
            conditions_results.at[ind, 'Run_forward'] = False
            break

        # take three IRs
        print('yield is nice')
        # easiest: no triggering but extraction from working live data visualisation



        # check if any pump stalled, if so, set the bool false, else true
        if pump_thionyl_chloride.is_moving() and pump_hexyldecanoic_acid.is_moving():
            True
        else:
            conditions_results.at[ind, 'Run_forward'] = False
            break
    else:
        pass


# after the whole for loop is over, drop that to a csv file.
# TODO make sure this doesn't overwrite previous runs
conditions_results.to_csv("flowchem/examples/experiments/results")



