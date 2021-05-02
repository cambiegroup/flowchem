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

    from lmfit import Minimizer, Parameters
    from lmfit.lineshapes import gaussian

    def residual(pars, x, data):
        """ Fitting model: 3 gaussian peaks centered at 1708, 1734 and 1796 cm-1 """
        model = (gaussian(x, pars['amp_1'], 1708, pars['wid_1']) +
                 gaussian(x, pars['amp_2'], 1734, pars['wid_2']) +
                 gaussian(x, pars['amp_3'], 1796, pars['wid_3']))
        return model - data

    pfit = Parameters()
    pfit.add(name='amp_1', value=0.50, min=0)
    pfit.add(name='amp_2', value=0.50, min=0)
    pfit.add(name='amp_3', value=0.50, min=0)
    pfit.add(name='wid_1', value=2, min=4, max=12)
    pfit.add(name='wid_2', value=5, min=5, max=15)
    pfit.add(name='wid_3', value=5, min=10, max=30)

    mini = Minimizer(residual, pfit, fcn_args=(x_arr, y_arr))
    out = mini.leastsq()
    # Get fitted gaussians
    g1 = gaussian(x_arr, out.params["amp_1"], 1708, out.params["wid_1"])
    g2 = gaussian(x_arr, out.params["amp_2"], 1734, out.params["wid_2"])
    g3 = gaussian(x_arr, out.params["amp_3"], 1796, out.params["wid_3"])

    # Calculate yield based on fitted peaks (less sensitive to baseline drift)
    sm = scipy.integrate.trapezoid(g1 + g2, x_arr)
    p = scipy.integrate.trapezoid(g3, x_arr)
    integral_p.append(p / (sm + p))

plt.scatter(x=list(range(291)), y=integral_p)
plt.show()
input()
