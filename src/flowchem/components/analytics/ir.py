"""An IR control component."""
from pydantic import BaseModel

from flowchem.components.flowchem_component import FlowchemComponent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class IRSpectrum(BaseModel):
    """IR spectrum class.

    Consider rampy for advance features (baseline fit, etc.)
    See e.g. https://github.com/charlesll/rampy/blob/master/examples/baseline_fit.ipynb
    """

    wavenumber: list[float]
    intensity: list[float]


class IRControl(FlowchemComponent):
    def __init__(self, name: str, hw_device: "FlowchemDevice") -> None:
        """IR Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        self.add_api_route("/start-experiment", self.start_experiment, methods=["PUT"])
        self.add_api_route("/acquire-spectrum", self.acquire_spectrum, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

        # Ontology: high performance liquid chromatography instrument
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0001057",
        )
        self.component_info.type = "IR Control"

    async def start_experiment(self):
        """
        Start the programeted experiment according to the template provided in the config file
        """
        ...

    async def acquire_spectrum(self) -> IRSpectrum:  # type: ignore
        """
        Acquire an IR spectrum from the instrument.

        This method retrieves the most recent infrared (IR) spectrum acquired by the device.
        Depending on the `treated` parameter, it can return either a processed spectrum with background subtraction
        or a raw, unprocessed spectrum.

        The acquisition process works as follows:
        - If `treated` is True, the method returns a spectrum where background subtraction has been performed,
          providing a clean signal suitable for analysis. The treated spectrum is retrieved from the device's
          OPC UA node specified by `SPECTRA_TREATED` ("ns=2;s=Local.iCIR.Probe1.SpectraTreated").
        - If `treated` is False, the method returns the raw, unprocessed spectrum directly from the device,
          without any background correction. The raw spectrum is retrieved from the OPC UA node specified by
          `SPECTRA_RAW` ("ns=2;s=Local.iCIR.Probe1.SpectraRaw").

        Args:
            treated (bool): If True, perform background subtraction and return the treated spectrum.
                            If False, return the raw scan without any processing.

        Returns:
            IRSpectrum: The acquired IR spectrum, either treated or raw.
        """
        ...

    async def stop(self):
        """Stop acquisition and exit gracefully."""
        ...
