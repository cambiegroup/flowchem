""" Spinsolve module """
import asyncio
import pprint as pp
import queue
import threading
import warnings
from pathlib import Path
from typing import Optional, Union

from loguru import logger
from lxml import etree
from packaging import version
from unsync import unsync

from flowchem.components.devices.Magritek.msg_maker import (
    create_message,
    create_protocol_message,
    get_request,
    set_attribute,
    set_data_folder,
    set_user_data,
)
from flowchem.components.devices.Magritek.parser import (
    StatusNotification,
    parse_status_notification,
)
from flowchem.components.devices.Magritek.reader import Reader
from flowchem.components.properties import ActiveComponent


@unsync
async def get_streams_for_connection(
    host: str, port: str
):
    """
    Given a target (host, port) returns the corresponding asyncio streams (I/O).
    """
    try:
        read, write = await asyncio.open_connection(host, port)
    except Exception as e:
        raise ConnectionError(f"Error connecting to {host}:{port} -- {e}") from e
    return read, write


class Spinsolve(ActiveComponent):
    """
    Spinsolve class, gives access to the spectrometer remote control API
    """

    def __init__(
        self,
        host="127.0.0.1",
        **kwargs,
    ):
        """
        Constructor, actuates the connection upon instantiation.

        kwargs are: name, xml_schema
        """

        super().__init__(kwargs.get("name"))
        # IOs
        self._io_reader, self._io_writer = get_streams_for_connection(
            host, kwargs.get("port", "13000")
        ).result()

        # Queue needed for thread-safe operation, the reader is in a different thread
        self._replies: queue.Queue = queue.Queue()
        self._reader = Reader(self._replies, kwargs.get("xml_schema", None))
        threading.Thread(
            target=self.connenction_listener_thread(), daemon=True
        ).start()

        # Check if the instrument is connected
        hw_info = self.hw_request()

        # If not raise ConnectionError
        if hw_info.find(".//ConnectedToHardware").text != "true":
            raise ConnectionError(
                "The spectrometer is not connected to the control PC running Spinsolve software!"
            )

        # If connected parse and log instrument info
        self.software_version = hw_info.find(".//SpinsolveSoftware").text
        self.hardware_type = hw_info.find(".//SpinsolveType").text
        logger.debug(
            f"Connected with Spinsolve model {self.hardware_type}, SW version: {self.software_version}"
        )

        # Load available protocols
        self.protocols_option = self.request_available_protocols()

        # Set experimental variable
        self.data_folder = kwargs.get("data_folder")

        # An optional mapping between remote and local folder location can be used for remote use
        self._folder_mapper = kwargs.get("remote_to_local_mapping")
        # Ensure mapper validity before starting. This will save you time later ;)
        if self._folder_mapper is not None:
            assert self._folder_mapper(self.data_folder) is not None

        # Sets default sample, solvent value and user data
        self.sample = kwargs.get("sample_name", "FlowChem Experiment")
        self.solvent = kwargs.get("solvent", "Chloroform?")
        self.user_data = dict(control_software="flowchem")

        # Finally, check version
        if version.parse(self.software_version) < version.parse("1.18.1.3062"):
            warnings.warn(
                f"Spinsolve version {self.software_version} is older than the reference (1.18.1.3062)"
            )

    def connenction_listener_thread(self):
        """Thread that listens to the connection and parses the reply"""
        self.connection_listener().result()

    @unsync
    async def connection_listener(self):
        """
        Listen for replies and puts them in the queue
        """
        while True:
            try:
                chunk = await self._io_reader.readuntil(b"</Message>")
            except asyncio.CancelledError:
                break
            self._replies.put(chunk)

    @unsync
    async def _transmit(self, message: bytes):
        """
        Sends the message to the spectrometer
        """
        self._io_writer.write(message)
        await self._io_writer.drain()

    @property
    def solvent(self) -> str:
        """Get current solvent"""
        # Send request
        self.send_message(get_request("Solvent"))

        # Get reply
        reply = self._read_reply(reply_type="GetResponse")

        # Parse and return
        return reply.find(".//Solvent").text

    @solvent.setter
    def solvent(self, solvent: str):
        """Sets the solvent"""
        self.send_message(set_attribute("Solvent", solvent))

    @property
    def sample(self) -> str:
        """Get current solvent (appears in acqu.par)"""
        # Send request
        self.send_message(get_request("Sample"))

        # Get reply
        reply = self._read_reply(reply_type="GetResponse")

        # Parse and return
        return reply.find(".//Sample").text

    @sample.setter
    def sample(self, sample: str):
        """Sets the sample name (appears in acqu.par)"""
        self.send_message(set_attribute("Sample", sample))

    @property
    def data_folder(self):
        """Get current data_folder location"""
        return self._data_folder  # No command available to directly query Spinsolve :(

    @data_folder.setter
    def data_folder(self, location: str):
        """Sets the location provided as data folder. optionally, with typeThese are included in acq.par"""
        if location is not None:
            self._data_folder = location
            self.send_message(set_data_folder(location))

    @property
    def user_data(self) -> dict:
        """Create a get user data request and parse result"""
        # Send request
        self.send_message(get_request("UserData"))

        # Get reply
        reply = self._read_reply(reply_type="GetResponse")

        # Parse and return
        return {
            data_item.get("key"): data_item.get("value")
            for data_item in reply.findall(".//Data")
        }

    @user_data.setter
    def user_data(self, data_to_be_set: dict):
        """Sets the user data proewqvided in the dict. These are included in acq.par"""
        self.send_message(set_user_data(data_to_be_set))

    def _read_reply(self, reply_type="", timeout=5):
        """Looks in the received replies for one of type reply_type"""
        # Get reply of reply_type from the reader object that holds the StreamReader
        reply = self._reader.wait_for_reply(reply_type=reply_type, timeout=timeout)
        logger.debug(f"Got a reply from spectrometer: {etree.tostring(reply)}")

        return reply

    async def _async_read_reply(self, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_reply, *args)

    def send_message(self, root: etree.Element):
        """
        Sends the tree connected XML etree.Element provided
        """
        # Turn the etree.Element provided into an ElementTree
        tree = etree.ElementTree(root)

        # Export to string with declaration
        message = etree.tostring(tree, xml_declaration=True, encoding="utf-8")

        # Transmit
        logger.debug(f"Transmitting request to spectrometer: {message}")
        self._transmit(message).result()

    def hw_request(self):
        """
        Sends an HW request to the spectrometer, receive the reply and returns it
        """
        self.send_message(create_message("HardwareRequest"))
        # Larger timeout than usual as this is the first request sent to the spectrometer
        # When the PC/Spinsolve is in standby, the reply to the first req is slower than usual
        return self._read_reply(reply_type="HardwareResponse", timeout=15)

    def request_available_protocols(self) -> dict:
        """
        Get a list of available protocol on the current spectrometer
        """
        # Request available protocols
        self.send_message(create_message("AvailableProtocolOptionsRequest"))
        # Get reply
        tree = self._read_reply(reply_type="AvailableProtocolOptionsResponse")

        # Parse reply and construct the dict with protocols available
        protocols = {}
        for element in tree.findall(".//Protocol"):
            protocol_name = element.get("protocol")
            protocols[protocol_name] = {
                option.get("name"): [value.text for value in option.findall("Value")]
                for option in element.findall("Option")
            }

        return protocols

    async def run_protocol(
        self, protocol_name, protocol_options=None
    ) -> Optional[Union[str, Path]]:
        """
        Runs a protocol

        Returns true if the protocol is started correctly, false otherwise.
        """
        # All protocol names are UPPERCASE, so force upper here to avoid case issues
        protocol_name = protocol_name.upper()
        if not self.is_protocol_available(protocol_name):
            warnings.warn(
                f"The protocol requested '{protocol_name}' is not available on the spectrometer!\n"
                f"Valid options are: {pp.pformat(sorted(self.protocols_option.keys()))}"
            )
            return None

        # Validate protocol options (check values and remove invalid ones, with warning)
        valid_protocol_options = self._validate_protocol_request(
            protocol_name, protocol_options
        )

        # Start protocol
        self._reader.clear_replies()
        self.send_message(
            create_protocol_message(protocol_name, valid_protocol_options)
        )

        # Follow status notifications and finally get location of remote data
        remote_data_folder = await self.check_notifications()
        logger.info(f"Protocol over - remote data folder is {remote_data_folder}")

        # If a folder mapper is present use it to translate the location
        if self._folder_mapper:
            return self._folder_mapper(remote_data_folder)
        return remote_data_folder

    async def check_notifications(self) -> Path:
        """
        Read all the StatusNotification and returns the dataFolder
        """
        remote_folder = Path(".")
        while True:
            # Get all StatusNotification
            # status_update = self._read_reply("StatusNotification", 6000)
            status_update = await self._async_read_reply("StatusNotification", 6000)

            # Parse them
            status, folder = parse_status_notification(status_update)
            logger.debug(f"Status update: Status is {status} and data folder={folder}")

            # When I get a response with folder, save the location!
            if folder:
                remote_folder = Path(folder)

            # If it is complete leave loop
            if status is StatusNotification.COMPLETED:
                break

            if status is StatusNotification.ERROR:
                warnings.warn(
                    "Error detected on running protocol -- aborting."
                )  # Usually device busy
                self.abort()  # Abort running experiment
                break
        return remote_folder

    def abort(self):
        """Abort current running command"""
        self.send_message(create_message("Abort"))

    def is_protocol_available(self, desired_protocol):
        """Check if the desired protocol is available on the current instrument"""
        return desired_protocol in self.protocols_option

    def _validate_protocol_request(self, protocol_name, protocol_options) -> dict:
        """Ensures the protocol names, option name and option values are valid."""
        # Valid option for protocol
        valid_options = self.protocols_option.get(protocol_name)
        if valid_options is None or protocol_options is None:
            return {}

        # For each option, check if valid. If not, remove it, raise warning and continue
        for option_name, option_value in list(protocol_options.items()):
            if option_name not in valid_options:
                protocol_options.pop(option_name)
                warnings.warn(
                    f"Invalid option {option_name} for protocol {protocol_name} -- DROPPED!"
                )
                continue

            # Get valid option values (list of them or empty list if not a multiple choice)
            valid_values = valid_options[option_name]

            # If there is no list of valid options accept anything
            if not valid_values:
                continue
            # otherwise validate the value as well
            elif str(option_value) not in valid_values:
                protocol_options.pop(option_name)
                warnings.warn(
                    f"Invalid value {option_value} for option {option_name} in protocol {protocol_name}"
                    f" -- DROPPED!"
                )

        # Returns the dict with only valid options/value pairs
        return protocol_options

    # def shim(self, shim_type="CheckShim") -> Tuple[float, float]:
    #     """ Perform one of the standard shimming routine {CheckShim | QuickShim | PowerShim} """
    #     # Check shim type
    #     if shim_type not in self.STD_SHIM_REQUEST:
    #         warnings.warn(f"Invalid shimming protocol: {shim_type} not in {self.STD_SHIM_REQUEST}. Assumed CheckShim")
    #         shim_type = "CheckShim"
    #
    #     # Submit request
    #     self.send_message(create_message(shim_type+"Request"))
    #
    #     # Wait for reply
    #     response_tag = shim_type + "Response"
    #     wait_time = {
    #         "CheckShim": 180,
    #         "QuickShim": 600,
    #         "PowerShim": 3600,
    #     }
    #     reply = self._read_reply(reply_type=response_tag, timeout=wait_time[shim_type])
    #
    #     # Check for errors
    #     error = reply.find(f".//{response_tag}").get("error")
    #     if error:
    #         warnings.warn(f"Error occurred during shimming: {error}")
    #         return None, None
    #
    #     # Return LineWidth and BaseWidth
    #     return float(reply.find(".//LineWidth").text), float(reply.find(".//BaseWidth").text)

    def shim(self):
        """Performs a shim on sample"""
        raise NotImplementedError("Use run protocol with a shimming protocol instead!")


if __name__ == "__main__":
    hostname = "BSMC-YMEF002121"

    nmr: Spinsolve = Spinsolve(host=hostname)
    print(nmr.sample)
