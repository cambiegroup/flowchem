from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.knauer.azura_compact_pump import AzuraCompactPump
from flowchem.devices.knauer.azura_compact_sensor import AzuraCompactSensor

from flowchem.devices.knauer.dad_component import (
    DADChannelControl,
    KnauerDADLampControl,
)
from flowchem.devices.knauer.knauer_valve import (KnauerValveHeads, KnauerInjectionValve,
                                                  Knauer6PortDistributionValve, Knauer12PortDistributionValve,
                                                  Knauer16PortDistributionValve)
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import pint


class VirtualAzuraCompact(FlowchemDevice):

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Azura"
        self.device_info.model = "Virtual Azura Compact"

        # All the following are set upon initialize()
        self.max_allowed_pressure = 0
        self.max_allowed_flow = 0
        self._headtype = None
        self._running: bool = None  # type: ignore
        self._pressure_max = kwargs.get("max_pressure", "10 bar")
        self._pressure_min = kwargs.get("min_pressure", "0 bar")

        self.rate = ureg.parse_expression("0 ml/min")

    async def initialize(self):
        # Set Pump and Sensor components.
        self.components.extend(
            [AzuraCompactPump("pump", self), AzuraCompactSensor("pressure", self)] # type: ignore
        )

    async def stop(self):
        logger.debug("VirtualAzura stopped")

    async def set_flow_rate(self, rate: pint.Quantity):
        logger.debug(f"Set flow rate to Azura {rate}")

    async def infuse(self):
        return True

    def is_running(self):
        return False

    async def read_pressure(self) -> pint.Quantity:
        return 10 * ureg.bar


class VirtualKnauerDAD(FlowchemDevice):

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Knauer"
        self.device_info.model = "Virtual DAD"

    async def initialize(self):

        self.components = [
            KnauerDADLampControl("d2", self), # type: ignore
            KnauerDADLampControl("hal", self), # type: ignore
        ]

        self.components.extend(
            [DADChannelControl(f"channel{n + 1}", self, n + 1) for n in range(4)] # type: ignore
        )

    async def status(self):
        return "ON"

    async def lamp(self, lamp: str, state: bool | str = "REQUEST") -> str:
        logger.debug(f"Set in Virtual KnauerDad the status to lamp {lamp} - {state}")
        return 'LAMP_D2:0'

    async def read_signal(self, channel: int) -> float:
        return 360

    async def set_wavelength(self, channel: int, wavelength: int) -> str:
        logger.debug(f"Set the wavelength {wavelength} in channel {channel} - Virtual KnauerDad")
        return "ok"

    async def integration_time(self, integ_time: int | str = "?") -> str | int:
        return 0

    async def bandwidth(self, bw: str | int) -> str | int:
        logger.debug(f"Set the bandwidth {bw} - Virtual KnauerDad")
        return 0


class VirtualKnauerValve(FlowchemDevice):

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Azura"
        self.device_info.model = "Virtual Valve"

        self._vale_type = kwargs.get("valve_type", "6")
        if self._vale_type == "LI":
            self._raw_position = "L"
        else:
            self._raw_position = "1"

            # The _raw_position must be always str!

    async def initialize(self):

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
        match self.device_info.additional_info["valve-type"]:
            case KnauerValveHeads.SIX_PORT_TWO_POSITION:
                valve_component = KnauerInjectionValve("injection-valve", self) # type: ignore
            case KnauerValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Knauer6PortDistributionValve("distribution-valve", self) # type: ignore
            case KnauerValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Knauer12PortDistributionValve("distribution-valve", self) # type: ignore
            case KnauerValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Knauer16PortDistributionValve("distribution-valve", self) # type: ignore
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    async def get_raw_position(self) -> str:
        return self._raw_position

    async def set_raw_position(self, position: str) -> bool:
        if type(position) is not str:
            position = str(position)
        logger.info(f"Set raw_position in the Virtual Knauer Valve {position}")
        self._raw_position = position
        return True

    async def get_valve_type(self) -> KnauerValveHeads:
        headtype = KnauerValveHeads(self._vale_type)
        return headtype