import pint
from flowchem.components.analytics.hplc import HPLCControl
from flowchem.components.analytics.ir import IRControl, IRSpectrum
from flowchem.components.analytics.nmr import NMRControl

from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.pumps.hplc_pump import HPLCPump

from flowchem.components.sensors.photo_sensor import PhotoSensor
from flowchem.components.sensors.pressure_sensor import PressureSensor

from flowchem.components.technical.photo import Photoreactor
from flowchem.components.technical.pressure import PressureControl
from flowchem.components.technical.power import PowerControl
from flowchem.components.technical.temperature import TemperatureControl, TempRange

from flowchem.components.valves.distribution_valves import SixPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve

from flowchem.devices.flowchem_device import FlowchemDevice

""" Analytics """

class FakeHPLC(HPLCControl):

    async def send_method(self, method_name):
        return True

    async def run_sample(self, sample_name: str, method_name: str):
        return True


class FakeIRC(IRControl):

    async def acquire_spectrum(self) -> IRSpectrum:
        return IRSpectrum()


class FakeNMR(NMRControl):
    ...


""" Pumps """

class FakeHPLCPump(HPLCPump):
    ...


class FakePump(SyringePump):

    async def infuse(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Start infusion."""
        return True

    async def stop(self):  # type: ignore
        """Stop pumping."""
        ...

    async def is_pumping(self) -> bool:  # type: ignore
        """Is pump running?"""
        return True

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        return True

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Pump in the opposite direction of infuse."""
        return True


""" Sensors """

class FakePhotoSensor(PhotoSensor):
    ...


class FakePressureSensor(PressureSensor):

    async def read_pressure(self, units: str = "bar") -> bool:
        """
        Read the current pressure from the sensor and return it in the specified units.

        Parameters:
        -----------
        units : str, optional
            The units in which to return the pressure (default is bar).

        Returns:
        --------
        float
            The current pressure in the specified units.
        """
        return 0.5


""" Technical """

class FakePhotoreactor(Photoreactor):
    ...


class FakePressureControl(PressureControl):

    async def set_pressure(self, pressure: str):
        ...


class FakePowerControl(PowerControl):
    ...


class FakeTemperatureControl(TemperatureControl):

    async def set_temperature(self, temp: str):
        ...


""" Valves """

class FakeValveDistribution(SixPortDistributionValve):

    def __init__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)
        self.identifier = "distribution"

    def _change_connections(self, raw_position: int | str, reverse: bool = False):
        if reverse:
            return raw_position #- 1
        else:
            return raw_position #+ 1


class FakeValvePosition(SixPortTwoPositionValve):

    def __init__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)
        self.identifier = "position"

    def _change_connections(self, raw_position: int | str, reverse: bool = False):
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1



