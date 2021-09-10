import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from lmfit.models import LinearModel, PseudoVoigtModel
import pathlib

files=pathlib.Path(r"C:\Users\bs-flowlab\Documents\spectra").glob('spectrum_at_*.csv')

sns.set()

# iterate through files in folder

# sm = spectra_df[80]
# p = spectra_df[260]
# spectra_df.plot(y=[80, 260], use_index=True)
# plt.show()

#contruct model
peak_chloride = PseudoVoigtModel(prefix="chloride_")
peak_dimer = PseudoVoigtModel(prefix="dimer_")
peak_monomer = PseudoVoigtModel(prefix="monomer_")
offset = LinearModel()
model = peak_chloride + peak_dimer + peak_monomer + offset

pars = model.make_params()
pars["chloride_center"].set(value=1800, min=1790, max=1810)
pars["chloride_amplitude"].set(min=0)  # Positive peak
pars["chloride_sigma"].set(min=5, max=50)  # Set full width half maximum

pars["dimer_center"].set(value=1715, min=1706, max=1716)
pars["dimer_amplitude"].set(min=0)  # Positive peak
pars["dimer_sigma"].set(min=1, max=15)  # Set full width half maximum

pars["monomer_center"].set(value=1740, min=1734, max=1752)
pars["monomer_amplitude"].set(min=0)  # Positive peak
pars["monomer_sigma"].set(min=4, max=30)  # Set full width half maximum

integral_p = []
for file in files:

    # read in the individual csv file
    spectra_df = pd.read_csv(file)
    # Reduce to ROI, actually not necessary since alread done but doesn't hurt

# for x in range(1255,1305):
    x_arr = spectra_df['Unnamed: 0'].to_numpy()
    y_arr = spectra_df['0'].to_numpy()

    df = pd.DataFrame(y_arr, index=x_arr)
    result = model.fit(y_arr, pars, x=x_arr)
    plt.figure(1)
    plt.cla()
    plt.plot(x_arr, y_arr, 'ro', ms=6)
    plt.plot(x_arr, result.best_fit, 'b--')
    plt.draw()
    plt.pause(0.001)
    plt.savefig(file.name[:-4] + '_fit.png')

    product = result.values["chloride_amplitude"]
    sm = result.values["dimer_amplitude"] + result.values["monomer_amplitude"]
    integral_p.append(product / (sm + product))
    print(f"Spectrum {file} fitted! [Yield was {product / (sm + product)}]")
    plt.figure(2)
    plt.cla()
    plt.scatter(x=list(range(len(integral_p))), y=integral_p)
    plt.draw()
    # plt.show()
    plt.pause(0.001)
#
# plt.cla()
# plt.scatter(x=list(range(len(integral_p))), y=integral_p)
# plt.draw()
# plt.savefig(f"yield_trend.png")
# print("Finished!")
