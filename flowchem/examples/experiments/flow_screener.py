# ToDo
#  A)  for experiment:
#  OK 1) Create reasonable boundary conditions -> from experiment
#  OK 2) equivalents  and residence time are the x and y axis, yield the z.  Flow rates follow from residence time and equivalents
#  OK 3) within these, create a matrix with a reasonable number of points  -> 9 * 10? 1, 1.1, 1.2 - 1.9, 1-10 min. flowrate = Ivol / Rtime. from this, individual flow rates follow
#  TD 4) Iterate through these points, being the conditions for the experiment and do this 2 times, in orthogonal direction
#  B) for hardware and control
#  1) make sure that the syringes don't stall/empty with keepalive
#  2) set  flow rate for first point
#  3) start syringes once
#  4) wait for equilibration
#  5) measure spectra and calculate yield. repeat that 3 times
#  C) Inputs and outputs should be:
#  OK 1) a dictionary, also check what was used in the sugar optimizer, probably bendable. Go for pandas data frame
#  OK kind of 2) output needs to be condition and yield. Simply append yield to empty field in data frame?

# create the data frame with all the experiments to perform

#create two pump objects, and one spectrometer

#enter an experiment loop. at the end of execution, check if the pump is still running. Also measure 3 spectra and put results to df.

from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
import numpy as np
import pandas as pd

def flow_rates(volume, residence_time, equivalents):
    total_flow = volume/residence_time
    # 0.1 is the concentration ratio
    flow_thio = total_flow*0.1*equivalents
    flow_acid = total_flow-flow_thio
    return round(flow_thio, 3), round(flow_acid, 3)

equivalents = np.arange(start=1, stop=2.1, step=0.1)
residence_times = np.arange(start=1, stop=11)

conditions_results = pd.DataFrame(columns=['residence_time', 'eq_thio','flow_thio', 'flow_acid', 'yield_1', 'yield_2', 'yield_3', 'yield_1_rev', 'yield_2_rev', 'yield_3_rev', 'forwards', 'backwards'])

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
    conditions_results.at[ind, 'flow_thio'], conditions_results.at[ind, 'flow_acid'] = flow_rates(2, conditions_results.at[ind, 'residence_time'] , conditions_results.at[ind, 'eq_thio'])

# Dataframe already is in the right order, now iterate through from top and from bottom, run the experiments and set the boolean



# Hardware

pump_connection = PumpIO('COM5')

pump_thionyl_chloride = Elite11(pump_connection, address=0)
pump_hexyldecanoic_acid = Elite11(pump_connection, address=1)

# hard parameters
reactor_volume = 2




# assume that the correct syringe diameter was manually set


# create dataframe
