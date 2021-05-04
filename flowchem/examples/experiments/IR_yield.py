import datetime
import scipy
import pandas as pd
import asyncio
from lmfit import Minimizer, Parameters
from lmfit.lineshapes import gaussian

from flowchem.devices.MettlerToledo.iCIR_async import FlowIR



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

# use non async
async def get_data():
    async with Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS, timeout=3600) as opcua_client:
        ir_spectrometer = FlowIR(opcua_client)

        # This will become a while true
        while True:
            # onyl check if new spectrum measured
            spectra_count = await ir_spectrometer.get_sample_count()
            while await ir_spectrometer.get_sample_count() == spectra_count:
                await asyncio.sleep(1)

            spectrum = await ir_spectrometer.get_last_spectrum_treated()
            # Restrict ROI to 1900 - 1600 cm-1

            spectrum_df = spectrum.as_df()

# this can become one function, taking a spectrum as a dataframe and calculating the yield from it

            spectrum_df.query(f"{1600} <= index <= {1900}", inplace=True)
            x_arr = spectrum_df.index.to_numpy()
            y_arr = spectrum_df[0]

            mini = Minimizer(residual, pfit, fcn_args=(x_arr, y_arr))
            out = mini.leastsq()
            # Get fitted gaussians
            g1 = gaussian(x_arr, out.params["amp_1"], 1708, out.params["wid_1"])
            g2 = gaussian(x_arr, out.params["amp_2"], 1734, out.params["wid_2"])
            g3 = gaussian(x_arr, out.params["amp_3"], 1796, out.params["wid_3"])

            # Calculate yield based on fitted peaks (less sensitive to baseline drift)
            acid = scipy.integrate.trapezoid(g1 + g2, x_arr)
            chloride = scipy.integrate.trapezoid(g3, x_arr)
            latest_yield = chloride/(chloride + acid)
            print(f"yield is {latest_yield}")

            latest_yield

# create one object just handling the ICIR communication. this should
