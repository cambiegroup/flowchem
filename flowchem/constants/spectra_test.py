import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from lmfit.models import LinearModel, PseudoVoigtModel

sns.set()

file = r"C:\Users\bs-flowlab\Documents\iC IR Experiments\alc0315_flow_chloride_test.csv"

spectra_df = pd.read_csv(file, index_col=0, names=list(range(291)), header=0)
# Reduce to ROI
spectra_df.query(f"{1600} <= index <= {1900}", inplace=True)

# sm = spectra_df[80]
# p = spectra_df[260]
# spectra_df.plot(y=[80, 260], use_index=True)
# plt.show()

integral_p = []
for x in range(291):
    x_arr = spectra_df.index.to_numpy()
    y_arr = spectra_df[x]

    df = pd.DataFrame(y_arr, index=x_arr)
    df.to_csv("acid_high_concentration.csv")

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

    result = model.fit(y_arr, pars, x=x_arr)

    plt.figure(1)
    plt.cla()
    plt.plot(x_arr, y_arr, 'ro', ms=6)
    plt.plot(x_arr, result.best_fit, 'b--')
    plt.draw()
    plt.pause(0.001)
    plt.savefig(f"fit_{x}.png")

    product = result.values["chloride_amplitude"]
    sm = result.values["dimer_amplitude"] + result.values["monomer_amplitude"]
    integral_p.append(product / (sm + product))
    print(f"Spectrum {x} fitted! [Yield was {product / (sm + product)}]")
    plt.figure(2)
    plt.cla()
    plt.scatter(x=list(range(len(integral_p))), y=integral_p)
    plt.draw()
    # plt.show()
    plt.pause(0.001)

plt.cla()
plt.scatter(x=list(range(len(integral_p))), y=integral_p)
plt.draw()
plt.savefig(f"yield_trend.png")
print("Finished!")
