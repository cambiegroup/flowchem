from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import samuel_saraiva
from .clarity_hplc_control import ClarityComponent
from loguru import logger
import asyncio


class VirtualClarity(FlowchemDevice):

    def __init__(self, name, **kwargs) -> None:

        super().__init__(name)

        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Clarity"
        self.device_info.model = "Virtual"

        self.instrument = 0

    async def initialize(self):
        """Start ClarityChrom and wait for it to be responsive."""
        logger.info("Virtual clarity startup")
        self.components.append(ClarityComponent(name="clarity", hw_device=self)) # type: ignore


    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """
        Simulate executing a ClarityChrom CLI command.

        Parameters:
        -----------
        command : str
            Command string to execute (without instrument specification).
        without_instrument_num : bool
            Skip adding instrument number parameter (for global commands).

        Returns:
        --------
        bool
            Always returns True to simulate successful command execution.
        """
        if without_instrument_num:
            cmd_string = f"Virtual Clarity command: {command}"
        else:
            cmd_string = f"Virtual Clarity command: i={self.instrument} {command}"

        logger.debug(f"Executing virtual Clarity command: {cmd_string}")
        # Simulate command execution delay
        await asyncio.sleep(0.1)
        # Simulate successful command execution
        return True