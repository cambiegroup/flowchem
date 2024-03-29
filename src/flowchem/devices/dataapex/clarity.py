"""Controls a local ClarityChrom instance via the CLI interface."""
# See https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm
import asyncio
from pathlib import Path
from shutil import which

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import jakob, wei_hsin

from .clarity_hplc_control import ClarityComponent


class Clarity(FlowchemDevice):
    def __init__(
        self,
        name,
        executable: str = r"C:\claritychrom\bin\claritychrom.exe",
        instrument_number: int = 1,
        startup_time: float = 20,
        startup_method: str = "",
        cmd_timeout: float = 3,
        user: str = "admin",
        password: str = "",
        cfg_file: str = "",
    ) -> None:
        super().__init__(name=name)
        # Metadata
        self.device_info.authors = [jakob, wei_hsin]
        self.device_info.manufacturer = "DataApex"
        self.device_info.model = "Clarity Chromatography"

        # Validate executable
        if which(executable):
            self.executable = executable
        else:
            assert '"' not in executable
            self.executable = f'"{executable}"'
        assert which(executable) or Path(executable).is_file(), "Valid executable found"

        # Save instance variables
        self.instrument = instrument_number
        self.startup_time = startup_time
        self.cmd_timeout = cmd_timeout

        # Pre-form initialization command to avoid passing tons of vars to initialize()
        self._init_command = ""
        self._init_command += f" cfg={cfg_file}" if cfg_file else ""
        self._init_command += f" u={user}" if user else ""
        self._init_command += f" p={password}" if password else ""
        self._init_command += f' "{startup_method}"'

    async def initialize(self):
        """Start ClarityChrom and wait for it to be responsive."""
        await self.execute_command(self._init_command)
        logger.info(f"Clarity startup: waiting {self.startup_time} seconds")
        await asyncio.sleep(self.startup_time)
        self.components.append(ClarityComponent(name="clarity", hw_device=self))

    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """Execute claritychrom.exe command."""
        if without_instrument_num:
            cmd_string = self.executable + f" {command}"
        else:
            cmd_string = self.executable + f" i={self.instrument} {command}"

        logger.debug(f"Executing Clarity command `{command}`")
        process = await asyncio.create_subprocess_shell(cmd_string)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.cmd_timeout)
            return True
        except TimeoutError:
            logger.error(f"Subprocess timeout expired (timeout = {self.cmd_timeout} s)")
            return False
