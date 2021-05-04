from lmfit.models import GaussianModel, LinearModel, LorentzianModel, PseudoVoigtModel
import pandas as pd
from matplotlib import pyplot as plt

df_chloride = pd.read_csv("chloride.csv", index_col=0)
print(df_chloride.head())
# df_chloride.plot()
df_chloride.query(f"{1600} <= index <= {1900}", inplace=True)
# df_chloride.plot()
# plt.show()

x_arr = df_chloride.index.to_numpy()
y_arr = df_chloride["chloride"]

# PseudoVoigtModel
# peak_chloride = GaussianModel(prefix="chloride_")
peak_chloride = PseudoVoigtModel(prefix="chloride_")
# peak_chloride = LorentzianModel(prefix="chloride_")
offset = LinearModel()
model = peak_chloride + offset

pars = model.make_params()
pars["chloride_center"].set(value=1800, min=1790, max=1810)
pars["chloride_amplitude"].set(min=0)  # Positive peak
pars["chloride_sigma"].set(min=5, max=50)  # Set full width half maximum


result = model.fit(y_arr, pars, x=x_arr)
print(result.fit_report())

plt.plot(x_arr, y_arr, 'ro', ms=6)
plt.plot(x_arr, result.best_fit, 'b--')
plt.show()

