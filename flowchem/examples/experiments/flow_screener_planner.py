import numpy as np
import pandas as pd
import pathlib

# hard parameters
reactor_volume = 0.05

def flow_rates(volume, residence_time, equivalents):
    """
    Given volume in ml, residence time in min and equivalents of SOCl2 returns the respective flowrates (ml/min)
    The concentration of the SOCl2 stream is 10x the acid and the equivalents are SOCl2 to acid.
    """
    total_flow = volume/residence_time
    # 0.1 is the concentration ratio, so...
    ratio_thio = equivalents * 0.1
    # flow_thio = flow_acid * ratio_thio
    # flow_thio + flow_acid = total_flow
    # Hence...
    flow_thio = (total_flow * ratio_thio) / (1+ratio_thio)
    flow_acid = total_flow - flow_thio
    return flow_thio, flow_acid


def calculate_flowrate(row):
    """ Function to be applied to the dataframe to populate flowrates """
    row['flow_thio'], row['flow_acid'] = flow_rates(reactor_volume, row['residence_time'], row['eq_thio'])
    return row


path_to_write_csv = pathlib.Path().home() / "Documents"

# prepare the IO Frame
equivalents = np.linspace(start=1, stop=1.3, num=6)  # [1. 1.06 1.12 1.18 1.24 1.3 ]
residence_times = np.logspace(start=0, stop=np.log(20), base=np.e, num=10)  # [ 1. 1.39495079  1.94588772  2.71441762  3.78647901  5.2819519,  7.368063   10.27808533 14.33742329 20.]

#use timestamp for identifier
conditions_results = pd.DataFrame(columns=['residence_time', 'eq_thio', 'flow_thio', 'flow_acid', 'yield_1', 'yield_2',
                                           'yield_3', 'yield_1_rev', 'yield_2_rev', 'yield_3_rev', 'Run_forward',
                                           'Run_backward', 'spectrum_1', 'spectrum_2',
                                           'spectrum_3', 'spectrum_1_rev', 'spectrum_2_rev', 'spectrum_3_rev'])


# Create tuples with (residence time, equivalents) for each experimental datapoint
experimental_conditions = [(t_res, eq) for t_res in residence_times for eq in equivalents]
# Adds conditions to dataframe
conditions_results['residence_time'], conditions_results['eq_thio'] = zip(*experimental_conditions)





# now, iterate through the dataframe and calculate the needed flow rates
conditions_results: pd.DataFrame = conditions_results.apply(calculate_flowrate, axis=1)
conditions_results.to_csv(path_to_write_csv / "flow_screening_empty.csv")
