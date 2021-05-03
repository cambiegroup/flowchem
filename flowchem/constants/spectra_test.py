import matplotlib.pyplot as plt
import pandas as pd
import scipy.integrate
import seaborn as sns

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

    from lmfit.models import GaussianModel, LinearModel, PseudoVoigtModel
    import matplotlib.pyplot as plt

    peak_chloride = PseudoVoigtModel(prefix="chloride_")
    peak2 = PseudoVoigtModel(prefix="p2_")
    peak3 = PseudoVoigtModel(prefix="p3_")
    offset = LinearModel()
    model = peak_chloride + peak2 + peak3 + offset

    pars = model.make_params()
    pars["chloride_center"].set(value=1800, min=1790, max=1810)
    pars["chloride_amplitude"].set(min=0)  # Positive peak
    pars["chloride_sigma"].set(min=5, max=50)  # Set full width half maximum

    pars["p2_center"].set(value=1736, min=1734, max=1738)
    pars["p2_amplitude"].set(min=0)  # Positive peak
    pars["p2_sigma"].set(min=4, max=40)  # Set full width half maximum

    pars["p3_center"].set(value=1708, min=1710, max=1712)
    pars["p3_amplitude"].set(min=0)  # Positive peak
    pars["p3_sigma"].set(min=0, max=10)  # Set full width half maximum

    result = model.fit(y_arr, pars, x=x_arr)

    plt.figure(1)
    plt.cla()
    plt.plot(x_arr, y_arr, 'ro', ms=6)
    plt.plot(x_arr, result.best_fit, 'b--')
    plt.draw()
    plt.pause(0.001)
    plt.savefig(f"fit_{x}.png")

    product = result.values["chloride_amplitude"]
    sm = result.values["p2_amplitude"] + result.values["p3_amplitude"]
    integral_p.append(product / (sm + product))
    print(f"Spectrum {x} fitted!")
    plt.figure(2)
    plt.cla()
    plt.scatter(x=list(range(len(integral_p))), y=integral_p)
    plt.draw()
    # plt.show()
    plt.pause(0.001)

plt.cla()
plt.scatter(x=list(range(len(integral_p))), y=integral_p)
plt.show()
plt.savefig(f"yield_trend.png")
input()
