import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# FILES AND PATHS
WORKING_DIR = Path().home() / "Documents"
SOURCE_FILE = WORKING_DIR / "chlorination_T_study_17_05_21_ter_results.csv"

# Load xp data to run
xp_data = pd.read_csv(SOURCE_FILE, index_col=0)
xp_data.plot(x="T", y="yield", kind="scatter")
plt.show()

SOURCE_FILE2 = WORKING_DIR / "chlorination_T_study_17_05_21_quater_results.csv"

# Load xp data to run
xp_data = pd.read_csv(SOURCE_FILE2, index_col=0)
xp_data.plot(x="T", y="yield", kind="scatter")
plt.show()



# from flowchem.examples.experiments.step_one_chemometrics import measure_yield_step1
#
# iC_EXPORT_FOLDER = Path(r"C:\Users\bs-flowlab\Documents\iC IR Experiments")
# SOURCE_FILE2 = iC_EXPORT_FOLDER / "Step_one_automation1.csv"
#
# xp_data2 = pd.read_csv(SOURCE_FILE2, index_col=0)
# xp_data2.query(f"{1600} <= index <= {1900}", inplace=True)
# xp_data2 = xp_data2.drop(xp_data2.columns[range(1450)], axis="columns")
# integral_p = []
# for key, col in enumerate(xp_data2._iter_column_arrays()):
#     x_arr = xp_data2.index.to_numpy()
#     y_arr = col
#
#     df = pd.DataFrame(y_arr, index=x_arr)
#     ryield = measure_yield_step1(df)
#     integral_p.append(ryield)
#
#     print(f"Key {key} yield is {ryield}")
#
#     plt.figure(2)
#     plt.cla()
#     plt.scatter(x=list(range(len(integral_p))), y=integral_p)
#     plt.draw()
#     # plt.show()
#     plt.pause(0.001)
#
# plt.cla()
# plt.scatter(x=list(range(len(integral_p))), y=integral_p)
# plt.draw()
# plt.savefig(f"yield_trend.png")
# print("Finished!")
