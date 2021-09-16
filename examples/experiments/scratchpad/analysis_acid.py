from lmfit.models import GaussianModel, LinearModel, LorentzianModel, PseudoVoigtModel
import pandas as pd
from matplotlib import pyplot as plt

df_acid_dimer = pd.read_csv("acid_high_concentration.csv", index_col=0)
df_acid_std = pd.read_csv("hexyldecanoic_acid.csv", index_col=0)
df_acid_std.query(f"{1600} <= index <= {1900}", inplace=True)

# print(df_acid_dimer.head())
# df_acid_dimer.plot()
# plt.show()

x_arr = df_acid_dimer.index.to_numpy()
y_arr = df_acid_dimer["intensity"]

x_arr = df_acid_std.index.to_numpy()
y_arr = df_acid_std["hexyldecanoic_acid"]

# PseudoVoigtModel
peak_dimer = PseudoVoigtModel(prefix="dimer_")
peak_monomer = PseudoVoigtModel(prefix="monomer_")
offset = LinearModel()
model = peak_dimer + peak_monomer + offset

pars = model.make_params()
pars["dimer_center"].set(value=1715, min=1706, max=1716)
pars["dimer_amplitude"].set(min=0)  # Positive peak
pars["dimer_sigma"].set(min=1, max=15)  # Set full width half maximum

pars["monomer_center"].set(value=1740, min=1734, max=1752)
pars["monomer_amplitude"].set(min=0)  # Positive peak
pars["monomer_sigma"].set(min=4, max=30)  # Set full width half maximum

result = model.fit(y_arr, pars, x=x_arr)
print(result.fit_report())

plt.plot(x_arr, y_arr, 'ro', ms=6)
plt.plot(x_arr, result.best_fit, 'b--')
plt.show()
