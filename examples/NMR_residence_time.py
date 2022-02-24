import asyncio
from pathlib import Path

from flowchem.components.devices.Magritek import Spinsolve, NMRSpectrum


nmr = Spinsolve.from_config(host="localhost")
path = asyncio.run(nmr.run_protocol("1D FLUORINE+", {"Number": 8, 'AcquisitionTime': 1.64, 'RepetitionTime': 2, 'PulseAngle': 90}))

# path = Path(r"c:\projects\data\2022\02\24\121721-1D FLUORINE+-FlowChem Experiment")
spectrum = NMRSpectrum(path)
spectrum.plot()


