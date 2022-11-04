"""Controls a local ClarityChrom instance via the CLI interface."""
# See https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line
import asyncio
from pathlib import Path
from shutil import which

from loguru import logger

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

        # Executable is either path or command in PATH
        if which(executable):
            self.executable = executable
        else:
            assert _is_valid_string(executable)
            self.executable = f'"{executable}"'
        assert which(executable) or Path(executable).is_file(), "Valid executable found"

        self.instrument = instrument_number
        self.startup_time = startup_time
        self.startup_method = startup_method
        self.cmd_timeout = cmd_timeout
        self.user = user
        self.password = password
        self.cfg_file = cfg_file

        super().__init__(name=name)

        # Ontology: high performance liquid chromatography instrument
        # noinspection HttpUrlsUsage
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0001057")

    async def initialize(self):
        """Start ClarityChrom upon initialization."""
        init_command = ""
        init_command += f" cfg={self.cfg_file}" if self.cfg_file else ""
        init_command += f" u={self.user}" if self.user else ""
        init_command += f" p={self.password}" if self.password else ""
        assert _is_valid_string(self.startup_method)
        init_command += f' "{self.startup_method}"'

        # Start Clarity and wait for it to be responsive before any other command is sent
        await self.execute_command(init_command)
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

    async def set_sample_name(self, sample_name: str):
        """Sets the name of the sample for the next run."""
        assert _is_valid_string(sample_name)
        await self.execute_command(f'set_sample_name="{sample_name}"')

    async def set_method(self, method_name: str):
        """
        Sets the HPLC method (i.e. a file with .MET extension) to the instrument.

        Make sure to select 'Send Method to Instrument' option in Method Sending Options dialog in System Configuration.
        """
        assert _is_valid_string(method_name)
        await self.execute_command(f" {method_name}")

    async def run(self):
        """
        Run one analysis on the instrument. The sample name has to be set in advance via sample-name.

        Note that it takes at least 2 sec until the run actually starts (depending on instrument configuration).
        While the export of the chromatogram in e.g. ASCII format can be achieved programmatically via the CLI, the best
        solution is to enable automatic data export for all runs of the HPLC as the chromatogram will be automatically
        exported as soon as the run is finished.
        """
        await self.execute_command(
            f"run={self.instrument}", without_instrument_num=True
        )

    async def exit(self):
        """Exit Clarity Chrom."""
        await self.execute_command("exit", without_instrument_num=True)

    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """Execute claritychrom.exe command."""
        cmd_string = self.executable
        if not without_instrument_num:
            cmd_string += f" i={self.instrument}"
        cmd_string += f" {command}"

        logger.debug(f"I will execute `{cmd_string}`")

        process = await asyncio.create_subprocess_shell(cmd_string)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.cmd_timeout)
        except TimeoutError:
            logger.error(f"Subprocess timeout expired (timeout = {self.cmd_timeout} s)")

    def get_components(self):
        """Return an HPLC_Control component."""
        # FIXME
        ...
        # router.add_api_route("/run", self.run, methods=["PUT"])
        # router.add_api_route("/method", self.set_method, methods=["PUT"])
        # router.add_api_route("/sample-name", self.set_sample_name, methods=["PUT"])
        # router.add_api_route("/exit", self.exit, methods=["PUT"])
