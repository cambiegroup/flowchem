import pandas as pd
from pathlib import Path

# Target dataframe to be saved
conditions = pd.DataFrame(columns=['eq', 'tR', 'T'])

# Parameter range
equivalents = {1.1}  # {1, 1.05, 1.1, 1.15, 1.2}
residence_times = {5}
temperature = {30, 50, 70}

# Create df entry for each combination of parameter (fully factorial)
experimental_conditions = [(eq, t_res, temp) for temp in temperature for t_res in residence_times for eq in equivalents]
conditions['eq'], conditions['tR'], conditions['T'] = zip(*experimental_conditions)

# Destination file
path_to_write_csv = Path().home() / "Documents"
filename = path_to_write_csv / "chlorination_T_study_17_05_21.csv"
assert filename.exists() is False, f"File already existing! {filename}"
conditions.to_csv(filename)

print(f"Experiment file written in {filename}")
