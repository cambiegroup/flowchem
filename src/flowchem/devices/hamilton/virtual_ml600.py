from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.hamilton.ml600_pump import ML600Pump
from flowchem.devices.hamilton.ml600_valve import ML600LeftValve, ML600RightValve
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import pint


class VirtualML600(FlowchemDevice):
    """Virtual ML600 class to simulate the behavior of the real Hamilton ML600 syringe pump."""

    def __init__(
        self,
        name: str,
        **kwargs
    ) -> None:
        # Call the parent class constructor with the virtual HamiltonPumpIO
        super().__init__(name)

        # Override device info for virtual device
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer="Virtual Hamilton"
        self.device_info.model="Virtual ML600"

        self.raw_position = "1"
        self.config = {
            "default_infuse_rate": "1 ml/min",
            "default_withdraw_rate": "1 ml/min",
        }
        self.syringe_volume = ureg.Quantity(kwargs.get("syringe_volume", "10 ml"))
        self._current_volume = self.syringe_volume.magnitude
        self.dual_syringe = kwargs.get("dual_syringe", "") == "true"

    @classmethod
    def from_config(cls, **config):
        return cls(**config)

    async def initialize(self, hw_init=False, init_speed: str = "200 sec / stroke"):
        """Simulate initializing the virtual ML600 pump."""
        logger.info(f"Virtual ML600 {self.name} with syringe {self.syringe_volume} initialized!")
        if self.dual_syringe:
            self.components.extend([ML600Pump("left_pump", self, "B"), ML600Pump("right_pump", self, "C"),
                                    ML600LeftValve("left_valve", self), ML600RightValve("right_valve", self)])
        else:
            self.components.extend([ML600Pump("pump", self), ML600LeftValve("valve", self)]) # type: ignore

    async def get_current_volume(self, pump: str) -> pint.Quantity:
        """Return current syringe position in ml."""
        return ureg.Quantity(f"{self._current_volume} ml")  # type: ignore

    async def set_to_volume(self, target_volume: pint.Quantity, rate: pint.Quantity, pump: str):
        """Simulate setting the syringe to a target volume."""
        self._current_volume = target_volume.m_as("ml")  # type: ignore
        logger.info(f"Virtual ML600 {self.name} set to volume {target_volume} at rate {rate}")
        return True

    async def get_pump_status(self, pump: str = "") -> bool:
        """Simulate getting the pump status."""
        return False

    async def get_valve_status(self, valve: str = "") -> bool:
        """Simulate getting the valve status."""
        return True

    async def get_raw_position(self, target_component: str) -> str:
        return self.raw_position

    async def stop(self, pump: str) -> bool:
        """Stop and abort any running command."""
        return True

    async def set_raw_position(
            self,
            target_position: str,
            wait_for_movement_end: bool = True,
            counter_clockwise=False,
            target_component=None
    ):
        self.raw_position = str(target_position)
        logger.debug(f"{self.name} valve position set to position {target_position}, switching CCW")