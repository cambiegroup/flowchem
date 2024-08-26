"""Runze valve control."""
import warnings
from enum import Enum

from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.runze.runze_valve_component import (
    Runze6PortDistributionValve,
    Runze8PortDistributionValve,
    Runze10PortDistributionValve,
    Runze12PortDistributionValve,
    Runze16PortDistributionValve,
    RunzeInjectionValve,
)
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import miguel

class RunzeValveHeads(Enum):
    """5 different valve types can be used. 6, 8, 10, 12, 16 multi-position valves."""

    SIX_PORT_SIX_POSITION = "6"
    EIGHT_PORT_EIGHT_POSITION = "8"
    TEN_PORT_TEN_POSITION = "10"
    TWELVE_PORT_TWELVE_POSITION = "12"
    SIXTEEN_PORT_SIXTEEN_POSITION = "16"

#class RunzeValveIO:



class RunzeValve(FlowchemDevice):
    """
    Control Runze multi position valves.
    """

    def __init__(self, ip_address=None, mac_address=None, **kwargs) -> None:
        super().__init__(ip_address, mac_address, **kwargs)
        self.eol = b"\r\n"
        self.device_info = DeviceInfo(
            authors=[miguel],
            manufacturer="Runze",
            model="Valve",
        )

    async def initialize(self):
        """Initialize connection."""
        # The connection is established in KnauerEthernetDevice.initialize()
        await super().initialize()

        # Detect valve type
        self.device_info.additional_info["valve-type"] = await self.get_valve_type()

        # Set components
        valve_component: FlowchemComponent
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

    #TODO update errors
    @staticmethod
    def handle_errors(reply: str):
        """Return True if there are errors, False otherwise. Warns for errors."""
        #if not reply.startswith("E"):
        #    return

        if "E0" in reply:
            DeviceError(
                "The valve refused to switch.\n"
                "Replace the rotor seals of the valve or replace the motor drive unit.",
            )
        elif "E1" in reply:
            DeviceError(
                "Skipped switch: motor current too high!\n"
                "Replace the rotor seals of the valve.",
            )
        elif "E2" in reply:
            DeviceError(
                "Change from one valve position to the next takes too long.\n"
                "Replace the rotor seals of the valve.",
            )
        elif "E3" in reply:
            DeviceError(
                "Switch position of DIP 3 and 4 are not correct.\n"
                "Correct DIP switch 3 and 4.",
            )
        elif "E4" in reply:
            DeviceError(
                "Valve homing position not recognized.\n" "Readjust sensor board.",
            )
        elif "E5" in reply:
            DeviceError(
                "Switch position of DIP 1 and 2 are not correct.\n"
                "Correct DIP switch 1 and 2.",
            )
        elif "E6" in reply:
            DeviceError("Memory error.\n" "Power-cycle valve!")
        else:
            DeviceError("Unspecified error detected!")





if __name__ == "__main__":
    import asyncio

    v = RunzeValve(ip_address="192.168.1.176")

    async def main(valve):
        """Test function."""
        await valve.initialize()
        await valve.set_raw_position("I")
        print(await valve.get_raw_position())
        await valve.set_raw_position("L")
        print(await valve.get_raw_position())

    asyncio.run(main(v))