"""Controls a local ClarityChrom instance via the CLI interface."""
# See https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line
import asyncio
import sys
from pathlib import Path
from shutil import which
from typing import TypedDict

from loguru import logger

from flowchem.models.analytical_device import AnalyticalDevice


ClarityConfig = TypedDict(
    "ClarityConfig",
    {
        "startup-time": float,
        "startup-method": str,
        "cmd_timeout": float,
        "user": str,
        "password": str,
        "clarity-cfg-file": str,
    },
)


class Clarity(AnalyticalDevice):
    DEFAULT_CONFIG: ClarityConfig = {
        "startup-time": 20,
        "startup-method": "",
        "cmd_timeout": 3,
        "user": "admin",
        "password": "",
        "clarity-cfg-file": "",
    }

    def __init__(
        self,
        executable: str = r"C:\claritychrom\bin\claritychrom.exe",
        instrument_number: int = 1,
        name=None,
        **config,
    ):

        self.config: ClarityConfig = self.DEFAULT_CONFIG | config  # type: ignore
        self.instrument = instrument_number
        # Executable is either path or command in PATH
        if which(executable):
            self.exe = executable
        else:
            assert self._is_valid_string(executable)
            self.exe = f'"{executable}"'

        assert which(executable) or Path(executable).is_file()
        self.exe = executable

        super().__init__(name=name)

        # Ontology: high performance liquid chromatography instrument
        # noinspection HttpUrlsUsage
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0001057")

    def _is_valid_string(self, path: str):
        """Ensure no double-quote are present in the string"""
        return '"' not in path

    async def initialize(self):
        """Start ClarityChrom upon initialization."""
        init_command = ""
        init_command += (
            f" cfg={cfg}" if (cfg := self.config["clarity-cfg-file"]) else ""
        )
        init_command += f" u={user}"
        init_command += f" p={pwd}" if (pwd := self.config["password"]) else ""
        met = self.config.get("startup-method")
        assert self._is_valid_string(met)
        init_command += f' "{met}"'

        # Start Clarity and wait for it to be responsive before any other command is sent
        await self.execute_command(init_command)
        await asyncio.sleep(self.config["startup-time"])

    async def set_sample_name(self, sample_name: str):
        """Sets the name of the sample for the next run."""
        assert self._is_valid_string(sample_name)
        await self.execute_command(f'set_sample_name="{sample_name}"')

    async def set_method(self, method_name: str):
        """
        Sets the name of the sample for the next run.

        has to be done to open project, then method. Take care to select 'Send Method to Instrument' option in Method
        Sending Options dialog in System Configuration.
        """
        assert self._is_valid_string(method_name)
        await self.execute_command(f" {method_name}")

    async def run(self):
        """
        Run one analysis on the instrument. Sample name has to be set in advance.

        Care should be taken to activate automatic data export on HPLC. (can be done via command,
        but that only makes it more complicated). Takes at least 2 sec until the run actually starts.
        """
        await self.execute_command(
            f"run={self.instrument}", without_instrument_num=True
        )

    async def exit(self):
        """Exit Clarity Chrom."""
        await self.execute_command("exit", without_instrument_num=True)

    async def execute_command(self, command: str, without_instrument_num: bool = False):
        """Execute claritychrom.exe command."""
        cmd_string = self.exe
        if not without_instrument_num:
            cmd_string += f" i={self.instrument}"
        cmd_string += f" {command}"

        logger.debug(f"I will execute `{cmd_string}`")

        process = await asyncio.create_subprocess_shell(cmd_string)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.config["cmd_timeout"])
        except TimeoutError:
            logger.error(
                f"Subprocess timeout expired (timeout = {self.config['cmd_timeout']} s)"
            )

    def get_router(self, prefix: str | None = None):
        """Create an APIRouter for this object."""
        router = super().get_router(prefix)
        router.add_api_route("/sample-name", self.set_sample_name, methods=["PUT"])
        router.add_api_route("/method", self.set_method, methods=["PUT"])
        router.add_api_route("/run", self.run, methods=["PUT"])
        router.add_api_route("/exit", self.exit, methods=["PUT"])
        return router
