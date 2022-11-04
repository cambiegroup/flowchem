"""Controls a local ClarityChrom instance via the CLI interface."""
# See https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line
import asyncio
from pathlib import Path
from shutil import which

from loguru import logger

from flowchem.components.hplc_control import HPLCControl
from flowchem.devices.flowchem_device import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.people import *


def _is_valid_string(path: str):
    """Ensure no double-quote are present in the string"""
    return '"' not in path


class Clarity(FlowchemDevice):
    def __init__(
        self,
        executable: str = r"C:\claritychrom\bin\claritychrom.exe",
        instrument_number: int = 1,
        startup_time: float = 20,
        startup_method: str = "",
        cmd_timeout: float = 3,
        user: str = "admin",
        password: str = "",
        cfg_file: str = "",
        name=None,
    ):
        super().__init__(name=name)

        # Validate executable
        if which(executable):
            self.executable = executable
        else:
            assert _is_valid_string(executable)
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

    def metadata(self) -> DeviceInfo:
        """Return hw device metadata."""
        return DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            maintainers=[dario],
            manufacturer="DataApex",
            model="Clarity Chromatography",
        )

    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """Execute claritychrom.exe command."""
        assert _is_valid_string(command)
        logger.debug(f"Executing Clarity command `{command}`")

        if without_instrument_num:
            cmd_string = self.executable + f" {command}"
        else:
            cmd_string = self.executable + f" i={self.instrument} {command}"

        process = await asyncio.create_subprocess_shell(cmd_string)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.cmd_timeout)
            return True
        except TimeoutError:
            logger.error(f"Subprocess timeout expired (timeout = {self.cmd_timeout} s)")
            return False

    def get_components(self):
        """Return an HPLC_Control component."""
        return (ClarityComponent(name="clarity", hw_device=self),)


class ClarityComponent(HPLCControl):
    hw_device: Clarity  # for typing's sake

    def __init__(self, name: str, hw_device: Clarity):
        """Device-specific initialization."""
        super().__init__(name, hw_device)
        # Clarity-specific command
        self.add_api_route("/exit", self.exit, methods=["PUT"])

    async def exit(self) -> bool:
        """Exit Clarity Chrom."""
        return await self.hw_device.execute_command("exit", without_instrument_num=True)

    async def send_method(self, method_name) -> bool:
        """
        Sets the HPLC method (i.e. a file with .MET extension) to the instrument.

        Make sure to select 'Send Method to Instrument' option in Method Sending Options dialog in System Configuration.
        """
        return await self.hw_device.execute_command(f" {method_name}")

    async def run_sample(self, sample_name: str, method_name: str) -> bool:
        """
        Run one analysis on the instrument.

        Note that it takes at least 2 sec until the run actually starts (depending on instrument configuration).
        While the export of the chromatogram in e.g. ASCII format can be achieved programmatically via the CLI, the best
        solution is to enable automatic data export for all runs of the HPLC as the chromatogram will be automatically
        exported as soon as the run is finished.
        """
        if not await self.hw_device.execute_command(f'set_sample_name="{sample_name}"'):
            return False
        if not await self.send_method(method_name):
            return False
        return await self.hw_device.execute_command(
            f"run={self.hw_device.instrument}", without_instrument_num=True
        )
