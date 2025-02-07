from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.distribution_valves import SixPortDistributionValve
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve
from flowchem.components.sensors.pressure_sensor import PressureSensor
from flowchem.devices.flowchem_device import FlowchemDevice


class FakePump(SyringePump):

    def __init__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)

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


class FakePressureSensor(PressureSensor):

    def __init__(self, name: str, hw_device: FlowchemDevice):
        super().__init__(name, hw_device)

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


