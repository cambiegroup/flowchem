from lmfit.models import LinearModel, PseudoVoigtModel

# create the fitting parameters
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


def calculate_step_one_yield(spectrum_df):
    """
    Given a spectrum calculate reaction yield
    """
    spectrum_df.query(f"{1600} <= index <= {1900}", inplace=True)
    x_arr = spectrum_df.index.to_numpy()
    y_arr = spectrum_df[0]

    result = model.fit(y_arr, pars, x=x_arr)
    product = result.values["chloride_amplitude"]
    sm = result.values["dimer_amplitude"] + result.values["monomer_amplitude"]
    latest_yield = product / (sm + product)

    # TODO: use peak at 1250 cm-1 to report SOCl2 left!
    return latest_yield
