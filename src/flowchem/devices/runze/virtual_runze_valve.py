from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze.runze_valve_component import (Runze16PortDistributionValve, Runze10PortDistributionValve,
                                                          Runze12PortDistributionValve, Runze6PortDistributionValve,
                                                          Runze8PortDistributionValve)
from flowchem.devices.runze.runze_valve import RunzeValveHeads
from flowchem.utils.people import samuel_saraiva
from loguru import logger


class VirtualRunzeValve(FlowchemDevice):

    def __init__(self, name="", **kwargs):
        """Virtual Control class for Ranze Valve."""
        super().__init__(name)
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Runze"
        self.device_info.model = "Virtual"

        self._vale_type = kwargs.get("valve_type", "6")
        self._position = "1"

    async def initialize(self):

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        match self.device_info.additional_info["valve-type"]:
            case RunzeValveHeads.SIX_PORT_SIX_POSITION:
                valve_component = Runze6PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.EIGHT_PORT_EIGHT_POSITION:
                valve_component = Runze8PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TEN_PORT_TEN_POSITION:
                valve_component = Runze10PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.TWELVE_PORT_TWELVE_POSITION:
                valve_component = Runze12PortDistributionValve(
                    "distribution-valve", self
                )
            case RunzeValveHeads.SIXTEEN_PORT_SIXTEEN_POSITION:
                valve_component = Runze16PortDistributionValve(
                    "distribution-valve", self
                )
            case _:
                raise RuntimeError("Unknown valve type")
        self.components.append(valve_component)

    async def get_raw_position(self, raise_errors: bool = False) -> str:
        return self._position

    async def set_raw_position(self, position: str | int, raise_errors: bool = True) -> bool:
        if isinstance(position, int):
            position = str(position)
        self._position = position
        logger.info(f"Virtual Valve position set to: {position}")
        return True

    async def get_valve_type(self) -> RunzeValveHeads:
        headtype = RunzeValveHeads(self._vale_type)
        return headtype

    @classmethod
    def from_config(cls, **config):
        return cls(
            address=config.get("address", 1),
            name=config.get("name", ""),
            valve_type=config.get("valve_type", "6")
        )


if __name__ == "__main__":
    import asyncio

    conf = {
        "port": "COM5",
        "address": 1,
        "name": "runze_test",
        "valve_type": "6"
    }
    v = VirtualRunzeValve.from_config(**conf)

    async def main(valve):
        """Test function."""
        await valve.initialize()
        position = await valve.components[0].set_monitor_position("2")
        print(position)
        print(await valve.components[0].get_monitor_position())
        connect = await valve.components[0].get_position()
        print(connect)
        await valve.components[0].get_position()
        await valve.components[0].set_position(connect="[[3, 0]]")

    asyncio.run(main(v))

