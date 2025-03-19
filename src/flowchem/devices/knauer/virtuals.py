from flowchem.devices.knauer.azura_compact import AzuraCompact, AzuraCompactPump, AzuraCompactSensor
from flowchem.devices.knauer.dad import KnauerDAD, KnauerDADLampControl, DADChannelControl
from flowchem.devices.knauer.knauer_valve import (KnauerValve, KnauerValveHeads, KnauerInjectionValve,
                                                  Knauer6PortDistributionValve, Knauer12PortDistributionValve,
                                                  Knauer16PortDistributionValve)
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import asyncio
import pint


class VirtualAzuraCompact(AzuraCompact):

    def __init__(
            self,
            ip_address=None,
            mac_address=None,
            max_pressure: str = "",
            min_pressure: str = "",
            **kwargs,
    ):
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Azura",
            model="Virtual Azura Compact",
        )
        self.name = kwargs.get("name", "")
        self.components = []

        # All the following are set upon initialize()
        self.max_allowed_pressure = 0
        self.max_allowed_flow = 0
        self._headtype = None
        self._running: bool = None  # type: ignore
        self._pressure_max = max_pressure
        self._pressure_min = min_pressure

        self.rate = ureg.parse_expression("0 ml/min")

    async def initialize(self):
        # Set Pump and Sensor components.
        self.components.extend(
            [AzuraCompactPump("pump", self), AzuraCompactSensor("pressure", self)]
        )

    async def stop(self):
        logger.debug("VirtualAzura stopped")

    async def set_flow_rate(self, rate: pint.Quantity):
        logger.debug(f"Set flow rate to Azura {rate}")

    async def infuse(self):
        return True

    async def read_pressure(self) -> pint.Quantity:
        return 10 * ureg.bar


class VirtualKnauerDAD(KnauerDAD):

    def __init__(
            self,
            ip_address: object = None,
            mac_address: object = None,
            name: str | None = None,
            turn_on_d2: bool = False,
            turn_on_halogen: bool = False,
            display_control: bool = True,
    ) -> None:
        self.eol = b"\n\r"
        self._d2 = turn_on_d2
        self._hal = turn_on_halogen
        self._state_d2 = False
        self._state_hal = False
        self._control = display_control  # True for Local
        self.name = name

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Knauer",
            model="Virtual DAD",
        )

    async def initialize(self):

        self.components = [
            KnauerDADLampControl("d2", self),
            KnauerDADLampControl("hal", self),
        ]

        self.components.extend(
            [DADChannelControl(f"channel{n + 1}", self, n + 1) for n in range(4)]
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


class VirtualKnauerValve(KnauerValve):

    def __init__(self, ip_address=None, mac_address=None, **kwargs):

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Knauer",
            model="Virtual Valve",
        )

        self.name = kwargs.get("name", "")
        self.components = []
        self._vale_type = kwargs.get("valve_type", "6")
        if self._vale_type == "LI":
            self._raw_position = "L"
        else:
            self._raw_position = "1"

    async def initialize(self):

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        match self.device_info.additional_info["valve-type"]:
            case KnauerValveHeads.SIX_PORT_TWO_POSITION:
                valve_component = KnauerInjectionValve("injection-valve", self)
            case KnauerValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Knauer6PortDistributionValve(
                    "distribution-valve", self
                )
            case KnauerValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Knauer12PortDistributionValve(
                    "distribution-valve", self
                )
            case KnauerValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Knauer16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    async def get_raw_position(self) -> str:
        return self._raw_position

    async def set_raw_position(self, position: str) -> bool:
        logger.debug(f"Set raw_position in the Virtual Knauer Valve {position}")
        self._raw_position = position
        return True

    async def get_valve_type(self):
        return KnauerValveHeads(self._vale_type)


if __name__ == "__main__":
    async def main():
        valve = VirtualKnauerValve(ip_address="", name="", valve_type="LI")
        await valve.initialize()
        pos = await valve.components[0].get_position()

    asyncio.run(main())
