import numpy as np
import pandas as pd
import pathlib

# hard parameters
reactor_volume = 0.5

def flow_rates(volume, residence_time, equivalents):
    """
    Given volume in ml, residence time in min and equivalents of Hexdiol returns the respective flowrates (ml/min)
    The concentration of the hexdiol stream is 4x the acid_chloride chloride and the equivalents are hexdiol to acid chloride.
    """
    total_flow = volume/residence_time
    # 0.1 is the concentration ratio, so...
    ratio_hexdiol = equivalents * 0.25
    # flow_hexdiol = flow_acid_chloride * ratio_hexdiol
    # flow_hexdiol + flow_acid_chloride = total_flow
    # Hence...
    flow_hexdiol = (total_flow * ratio_hexdiol) / (1+ratio_hexdiol)
    flow_acid_chloride = total_flow - flow_hexdiol
    return flow_hexdiol, flow_acid_chloride


def calculate_flowrate(row):
    """ Function to be applied to the dataframe to populate flowrates """
    row['flow_hexdiol'], row['flow_acid_chloride'] = flow_rates(reactor_volume, row['residence_time'], row['eq_hexdiol'])
    return row


path_to_write_csv = pathlib.Path().home() / "Documents"

# prepare the IO Frame
equivalents = [1, 2, 3, 4]#np.linspace(start=1, stop=1.3, num=6)  # [1. 1.06 1.12 1.18 1.24 1.3 ]
residence_times = [1, 5, 10,20]#np.logspace(start=0, stop=np.log(20), base=np.e, num=10)  # [ 1. 1.39495079  1.94588772  2.71441762  3.78647901  5.2819519,  7.368063   10.27808533 14.33742329 20.]


#use timestamp for identifier
conditions_results = pd.DataFrame(columns=['residence_time', 'eq_hexdiol', 'flow_hexdiol', 'flow_acid_chloride', 'yield_1', 'yield_2',
                                           'yield_3', 'yield_1_rev', 'yield_2_rev', 'yield_3_rev', 'Run_forward',
                                           'Run_backward', 'spectrum_1', 'spectrum_2',
                                           'spectrum_3', 'spectrum_1_rev', 'spectrum_2_rev', 'spectrum_3_rev'])


# Create tuples with (residence time, equivalents) for each experimental datapoint
experimental_conditions = [(t_res, eq) for t_res in residence_times for eq in equivalents]
# Adds conditions to dataframe
conditions_results['residence_time'], conditions_results['eq_hexdiol'] = zip(*experimental_conditions)


# now, iterate through the dataframe and calculate the needed flow rates
conditions_results: pd.DataFrame = conditions_results.apply(calculate_flowrate, axis=1)
# conditions_results.to_csv(path_to_write_csv / "flow_screening_times_hexdiol_const_empty.csv")
conditions_results.to_csv(path_to_write_csv / "test_acylation.csv")
