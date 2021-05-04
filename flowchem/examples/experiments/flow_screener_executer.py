# ToDo
#  A)  for experiment:
#  OK 1) Create reasonable boundary conditions -> from experiment
#  OK 2) equivalents  and residence time are the x and y axis, yield the z.  Flow rates follow from residence time and equivalents
#  OK 3) within these, create a matrix with a reasonable number of points  -> 9 * 10? 1, 1.1, 1.2 - 1.9, 1-10 min. flowrate = Ivol / Rtime. from this, individual flow rates follow
#  OK 4) Iterate through these points, being the conditions for the experiment and do this 2 times, in orthogonal direction
#  B) for hardware and control
#  OK 1) make sure that the syringes don't stall/empty with keepalive
#  OK 2) set  flow rate for first point
#  OK 3) start syringes once
#  OK 4) wait for equilibration
#  OK 5) measure spectra and calculate yield. repeat that 3 times
#  C) Inputs and outputs should be:
#  OK 1) a dictionary, also check what was used in the sugar optimizer, probably bendable. Go for pandas data frame
#  OK kind of 2) output needs to be condition and yield. Simply append yield to empty field in data frame?
#  MISSING: pseudovoigt & dropping the spectra to some folder, with identifier


from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
import opcua
from flowchem.devices.MettlerToledo.iCIR import FlowIR
import pandas as pd
from time import sleep, time
import scipy
from lmfit import Minimizer, Parameters
from lmfit.lineshapes import gaussian
from pathlib import Path


def residual(pars, x, data):
    """ Fitting model: 3 gaussian peaks centered at 1708, 1734 and 1796 cm-1 """
    model = (gaussian(x, pars['amp_1'], 1708, pars['wid_1']) +
             gaussian(x, pars['amp_2'], 1734, pars['wid_2']) +
             gaussian(x, pars['amp_3'], 1796, pars['wid_3']))
    return model - data


# create the fitting parameters
pfit = Parameters()
pfit.add(name='amp_1', value=0.50, min=0)
pfit.add(name='amp_2', value=0.50, min=0)
pfit.add(name='amp_3', value=0.50, min=0)
pfit.add(name='wid_1', value=2, min=4, max=12)
pfit.add(name='wid_2', value=5, min=5, max=15)
pfit.add(name='wid_3', value=5, min=10, max=30)


def calculate_yield(spectrum_df):
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
    latest_yield = chloride / (chloride + acid)
    print(f"yield is {latest_yield}")
    return latest_yield


path_to_write_csv = Path().home() / "Documents"

try:
    path_to_write_csv.joinpath("spectra").mkdir()
except FileExistsError:
    print('Directory already exists')


# Hardware
pump_connection = PumpIO('COM5')

pump_thionyl_chloride = Elite11(pump_connection, address=0)
pump_hexyldecanoic_acid = Elite11(pump_connection, address=6)

pump_thionyl_chloride.syringe_diameter = 9.62
pump_hexyldecanoic_acid.syringe_diameter = 19.93


###
# initialise the IR and make sure everything works
client = opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS)
ir_spectrometer = FlowIR(client)
if ir_spectrometer.is_iCIR_connected:
    print(f"FlowIR connected!")
else:
    print("FlowIR not connected :(")
    import sys
    sys.exit()

spectrum = ir_spectrometer.get_last_spectrum_treated()
while spectrum.empty:
    spectrum = ir_spectrometer.get_last_spectrum_treated()

###

try:
    conditions_results = pd.read_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))
except OSError:
    conditions_results = pd.read_csv(path_to_write_csv.joinpath("flow_screening_empty.csv"))

conditions_results.Run_forward = conditions_results.Run_forward.astype(str)
conditions_results.Run_backward = conditions_results.Run_backward.astype(str)

# Dataframe already is in the right order, now iterate through from top and from bottom, run the experiments and set the boolean
# assume that the correct syringe diameter was manually set
for ind in conditions_results.index:
    if conditions_results.at[ind, 'Run_forward'] != "Success":
        # also check the bool, if it ran already, don't rerun it. but skip it
        pump_thionyl_chloride.infusion_rate = conditions_results.at[ind, 'flow_thio']
        pump_hexyldecanoic_acid.infusion_rate = conditions_results.at[ind, 'flow_acid']

        # Ensures pumps are running
        if not pump_thionyl_chloride.is_moving():
            pump_thionyl_chloride.infuse_run()
        if not pump_hexyldecanoic_acid.is_moving():
            pump_hexyldecanoic_acid.infuse_run()

        print(f"Started experiment with residence time = {conditions_results.at[ind, 'residence_time']} and "
              f"SOCl2 equiv. = {conditions_results.at[ind, 'eq_thio']}! "
              f"Now waiting {3*60*conditions_results.at[ind, 'residence_time']}s...")
        # wait until several reactor volumes are through
        sleep(3*60*conditions_results.at[ind, 'residence_time'])

        # check if any pump stalled, if so, set the bool false, leave loop
        if not pump_thionyl_chloride.is_moving() or not pump_hexyldecanoic_acid.is_moving():
            conditions_results.at[ind, 'Run_forward'] = False
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))
            break

        # do this 3 times, just gets 3 consecutive spectra
        for x in range(3):
            spectra_count = ir_spectrometer.get_sample_count()

            while ir_spectrometer.get_sample_count() == spectra_count:
                sleep(1)

            print(f"New spectrum!")
            spectrum = ir_spectrometer.get_last_spectrum_treated()
            spectrum_df = spectrum.as_df()
            conditions_results.at[ind, f'yield_{x+1}'] = calculate_yield(spectrum_df)
            # create a unique identifier, in this case the current time in seconds
            ident = round(time())
            # drop the identifier to the table
            conditions_results.at[ind, f'spectrum_{x + 1}'] = ident
            # now drop the spectrum as csv to the spectrafolder
            spectrum_df.to_csv(path_to_write_csv.joinpath(f"spectra/spectrum_at_{ident}.csv"))


        # check if any pump stalled, if so, set the bool false, else true
        if not pump_thionyl_chloride.is_moving() or not pump_hexyldecanoic_acid.is_moving():
            conditions_results.at[ind, 'Run_forward'] = "Failed"
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))
            break
        else:
            conditions_results.at[ind, 'Run_forward'] = "Success"
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))


for ind in reversed(conditions_results.index):
    if conditions_results.at[ind, 'Run_backward']  != "Success":
        # also check the bool, if it ran already, don't rerun, but skip it
        pump_thionyl_chloride.infusion_rate = conditions_results.at[ind, 'flow_thio']
        pump_hexyldecanoic_acid.infusion_rate = conditions_results.at[ind, 'flow_acid']
        if pump_thionyl_chloride.is_moving() and pump_hexyldecanoic_acid.is_moving():
            pass
        else:
            pump_thionyl_chloride.infuse_run()
            pump_hexyldecanoic_acid.infuse_run()

        # wait until several reactor volumes are through
        sleep(3*60*conditions_results.at[ind, 'residence_time'])

        # check if any pump stalled, if so, set the bool false, leave loop
        if not pump_thionyl_chloride.is_moving() or not pump_hexyldecanoic_acid.is_moving():
            conditions_results.at[ind, 'Run_backward'] = "Failed"
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))
            break

        # do this 3 times, just gets 3 consecutive spectra
        for x in range(3):
            spectra_count = ir_spectrometer.get_sample_count()

            while ir_spectrometer.get_sample_count() == spectra_count:
                sleep(1)

            print(f"New spectrum!")
            spectrum = ir_spectrometer.get_last_spectrum_treated()
            spectrum_df = spectrum.as_df()
            # this now needs to be translated to yield
            conditions_results.at[ind, f'yield_{x+1}_rev'] = calculate_yield(spectrum_df)
            # create a unique identifier, in this case the current time in seconds
            ident = round(time())
            # drop the identifier to the table
            conditions_results.at[ind, f'spectrum_{x + 1}_rev'] = ident
            # now drop the spectrum as csv to the spectrafolder
            spectrum_df.to_csv(path_to_write_csv.joinpath(f"spectra/spectrum_at_{ident}.csv"))

        # check if any pump stalled, if so, set the bool false, else true
        if pump_thionyl_chloride.is_moving() and pump_hexyldecanoic_acid.is_moving():
            conditions_results.at[ind, 'Run_backward'] = "Success"
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))

        else:
            conditions_results.at[ind, 'Run_backward'] = "Failed"
            conditions_results.to_csv(path_to_write_csv.joinpath("flow_screening_experiment.csv"))

            break

pump_thionyl_chloride.stop()
pump_hexyldecanoic_acid.stop()



