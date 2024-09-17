from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem import __version__
from loguru import logger
from pathlib import Path
import os

from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from flowchem.devices.virtual import Chronology


class Chronology_Component(FlowchemComponent):
    """
    A component class that integrates the Chronology device with the Flowchem framework and provides an API for logging.

    This class extends FlowchemComponent to represent a Flowchem device along with additional functionality,
    such as the ability to set up logging through a specified API route.

    Attributes:
        name (str): The name of the component.
        hw_device (FlowchemDevice): The hardware device instance associated with this component.

    Methods:
        __init__(self, name: str, hw_device: FlowchemDevice):
            Initializes the Chronology_Component class by setting up the API route for logging and passing
            the device attributes to the base class.

        async set_logging(self, path: str):
            Creates a directory at the specified path if it doesn't exist and sets up logging.
            A new log file will be generated in the specified path with the filename 'log.log'.

            Args:
                path (str): The file path where the log directory should be created.

            Raises:
                OSError: If the directory creation fails.
    """

    def __init__(self, name: str, hw_device):
        """
        Initializes the Chronology_Component instance.

        Args:
            name (str): The name of the component.
            hw_device (FlowchemDevice): The hardware device associated with this component.

        The constructor also registers a new API route, "/set_logging", to allow external clients
        to configure logging to a specified directory.
        """
        hw_device: Chronology
        super().__init__(name, hw_device)
        self.add_api_route("/set_logging", self.set_logging, methods=["PUT"])

    async def set_logging(self, path: str, experiment_id: str | int):
        """
        Sets up logging to a file in the provided directory.

        This method creates a directory (if it doesn't exist) at the provided `path`, and sets up
        logging using Loguru. The log file will be saved at `path/log.log` with a log level of "INFO".

        Args:
            path (str): The directory where the log file should be created.
            experiment_id (str | int): The experimental id or name to be identify.

        Raises:
            OSError: If the directory cannot be created.
        """
        os.mkdir(path)

        current_time = time.localtime()

        # Extract the components
        year = current_time.tm_year
        month = current_time.tm_mon
        day = current_time.tm_mday
        hour = current_time.tm_hour
        minute = current_time.tm_min
        second = current_time.tm_sec

        devices_used = [dev.__class__.__name__ for dev in self.hw_device.flowchem.devices]

        msg = (f"The experiment starts in {year}-{month:02d}-{day:02d} at {hour:02d}:{minute:02d}:{second:02d}"
               f" using flowchem version {__version__}. It used the "
               f"devices: {devices_used} configured through the specifications below:\n\n"
               f"{self.hw_device.config_inf}\n\n"
               f"Client name/number: {self.hw_device.flowchem.mdns.mdns_addresses}. Name/id of the experiment:"
               f" {experiment_id}")

        with open(f"{path}/information.txt", 'w') as file:
            file.write(msg)
        logger.add(Path(path + "/log.log"), level="INFO")
