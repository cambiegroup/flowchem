from flowchem.utils.people import samuel_saraiva
from .clarity import Clarity
from loguru import logger
import asyncio


class VirtualClarity(Clarity):

    def __init__(
        self,
        name,
        executable: str = r"python",
        instrument_number: int = 1,
        startup_time: float = 1,
        startup_method: str = "",
        cmd_timeout: float = 3,
        user: str = "admin",
        password: str = "",
        cfg_file: str = "",
    ) -> None:

        super().__init__(name=name, executable="python", startup_time=startup_time)
        # Metadata
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual"
        self.device_info.model = "Virtual Clarity Chromatography"
        self.executable = f'"{executable}"'

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
        self._last_command = cmd_string

        # Simulate command execution delay
        await asyncio.sleep(0.1)

        # Simulate successful command execution
        return True