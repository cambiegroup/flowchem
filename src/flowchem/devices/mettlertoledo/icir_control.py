from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.analytics.ir import IRControl, IRSpectrum

if TYPE_CHECKING:
    from .icir import IcIR


class IcIRControl(IRControl):
    """
    IcIR Control component for handling IR spectrometer operations.

    Attributes:
        hw_device (IcIR): The hardware device for the IR spectrometer.
    """
    hw_device: IcIR  # for typing's sake

    def __init__(self, name: str, hw_device: IcIR) -> None:  # type:ignore
        """
        Initialize the IcIRControl component.

        Args:
            name (str): The name of the component.
            hw_device (IcIR): The hardware device instance for controlling the IR spectrometer.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/spectrum-count", self.spectrum_count, methods=["GET"])

    async def acquire_spectrum(self, treated: bool = True) -> IRSpectrum:
        """
        Acquire an IR spectrum.

        Args:
            treated (bool): If True, perform background subtraction. If False, return a raw scan.

        Returns:
            IRSpectrum: The acquired IR spectrum.
        """
        if treated:
            return await self.hw_device.last_spectrum_treated()
        else:
            return await self.hw_device.last_spectrum_raw()

    async def spectrum_count(self) -> int:
        """
        Get the count of acquired spectra.

        Returns:
            int: The number of spectra acquired. Returns -1 if the count is None.
        """
        count = await self.hw_device.sample_count()
        if count is not None:
            return count
        else:
            return -1

    async def stop(self):
        """
        Stop the ongoing IR experiment.

        Returns:
            bool: True if the experiment was successfully stopped, False otherwise.
        """
        return await self.hw_device.stop_experiment()
