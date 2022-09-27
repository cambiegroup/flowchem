""" Spinsolve module """
import asyncio
import pprint as pp
import warnings
from pathlib import Path

from fastapi import BackgroundTasks
from flowchem.devices.magritek._msg_maker import create_message
from flowchem.devices.magritek._msg_maker import create_protocol_message
from flowchem.devices.magritek._msg_maker import get_request
from flowchem.devices.magritek._msg_maker import set_attribute
from flowchem.devices.magritek._msg_maker import set_data_folder
from flowchem.devices.magritek._msg_maker import set_user_data
from flowchem.devices.magritek.utils import create_folder_mapper
from flowchem.devices.magritek.xml_parser import parse_status_notification
from flowchem.devices.magritek.xml_parser import StatusNotification
from flowchem.models.analytical_device import AnalyticalDevice
from loguru import logger
from lxml import etree
from packaging import version

from .utils import get_my_docs_path


class Spinsolve(AnalyticalDevice):
    """Spinsolve class, gives access to the spectrometer remote control API."""

    def __init__(
        self,
        host="127.0.0.1",
        port: int | None = 13000,
        name: str | None = None,
        xml_schema=None,
        data_folder=None,
        solvent: str | None = "Chloroform-d1",
        sample_name: str | None = "Unnamed automated experiment",
        remote_to_local_mapping: list[str] | None = None,
    ):
        """Controls a Spinsolve instance via HTTP XML API."""
        super().__init__(name)

        self.host, self.port = host, port

        # The Qs must exist before the response is received to be awaited
        # Could be generated programmatically from RemoteControl.xsd, but it's not worth it
        self._replies_by_type = {
            "HardwareResponse": asyncio.Queue(),
            "AvailableProtocolOptionsResponse": asyncio.Queue(),
            "GetResponse": asyncio.Queue(),
            "StatusNotification": asyncio.Queue(),
        }

        # Set experimental variable
        self._data_folder = data_folder

        # An optional mapping between remote and local folder location can be used for remote use
        if remote_to_local_mapping is not None:
            self._folder_mapper = create_folder_mapper(*remote_to_local_mapping)
            assert (
                self._folder_mapper(self._data_folder) is not None
            )  # Ensure mapper validity.
        else:
            self._folder_mapper = None  # type: ignore

        # Sets default sample, solvent value and user data
        self.sample, self.solvent = sample_name, solvent
        self.protocols_option: dict[str, dict] = {}
        self.user_data = {"control_software": "flowchem"}

        # XML schema for reply validation. Reply validation is completely optional!
        if xml_schema is None:
            # This is the default location upon Spinsolve installation.
            # However, remote control can be from remote, i.e. not Spinsolve PC so this ;)
            default_schema = (
                get_my_docs_path() / "Magritek" / "Spinsolve" / "RemoteControl.xsd"
            )
            try:
                self.schema = etree.XMLSchema(file=str(default_schema))
            except etree.XMLSchemaParseError:  # i.e. not found
                self.schema = None
        else:
            self.schema = xml_schema

        # IOs (these are set upon initialization w/ initialize)
        self._io_reader, self._io_writer, self.reader = None, None, None
        # Each protocol adds a new Path to the list, run_protocol returns the ID of the next protocol
        self._result_folders: list[Path] = []

        # Ontology metadata
        # fourier transformation NMR instrument
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0000487")

    async def initialize(self):
        """Initiate connection with a running Spinsolve instance."""
        # Get IOs
        try:
            self._io_reader, self._io_writer = await asyncio.open_connection(
                self.host, self.port
            )
            logger.debug(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            raise ConnectionError(
                f"Error connecting to {self.host}:{self.port} -- {e}"
            ) from e

        # Start reader thread
        self.reader = asyncio.create_task(
            self.connection_listener(), name="Connection listener"
        )

        # Check if the instrument is connected
        hw_info = await self.hw_request()

        # If not raise ConnectionError
        if hw_info.find(".//ConnectedToHardware").text != "true":
            raise ConnectionError(
                "The spectrometer is not connected to the control PC running Spinsolve software!"
            )

        # If connected parse and log instrument info
        software_version = hw_info.find(".//SpinsolveSoftware").text
        hardware_type = hw_info.find(".//SpinsolveType").text
        logger.debug(f"Connected to model {hardware_type}, SW: {software_version}")

        # Load available protocols
        self.protocols_option = await self.request_available_protocols()

        # Finally, check version
        if version.parse(software_version) < version.parse("1.18.1.3062"):
            warnings.warn(
                f"Spinsolve version {software_version} is older than the reference (1.18.1.3062)"
            )

        await self.set_data_folder(self._data_folder)

    async def connection_listener(self):
        """Listen for replies and puts them in the queue."""
        logger.debug("Spinsolve connection listener started!")
        parser = etree.XMLParser()
        while True:
            raw_tree = await self._io_reader.readuntil(b"</Message>")
            logger.debug(f"Read reply {raw_tree}")

            # Try parsing reply and skip if not valid
            try:
                parsed_tree = etree.fromstring(raw_tree, parser)
            except etree.XMLSyntaxError:
                warnings.warn(f"Cannot parse response XML {raw_tree}")
                continue

            # Validate reply if schema was provided
            if self.schema:
                try:
                    self.schema.validate(parsed_tree)
                except etree.XMLSyntaxError as syntax_error:
                    warnings.warn(
                        f"Invalid XML received! [Validation error: {syntax_error}]"
                    )

            # Add to reply queue of the given tag-type
            await self._replies_by_type[parsed_tree[0].tag].put(parsed_tree)

    async def _transmit(self, message: bytes):
        """
        Sends the message to the spectrometer
        """
        assert isinstance(
            self._io_writer, asyncio.StreamWriter
        ), "The connection was not initialized!"
        self._io_writer.write(message)
        await self._io_writer.drain()

    async def get_solvent(self) -> str:
        """Get current solvent"""
        await self.send_message(get_request("Solvent"))
        reply = await self._replies_by_type["GetResponse"].get()
        return reply.find(".//Solvent").text

    async def set_solvent(self, solvent: str):
        """Sets the solvent"""
        await self.send_message(set_attribute("Solvent", solvent))

    async def get_sample(self) -> str:
        """Get current solvent (appears in acqu.par)"""
        await self.send_message(get_request("Sample"))
        reply = await self._replies_by_type["GetResponse"].get()
        return reply.find(".//Sample").text

    async def set_sample(self, sample: str):
        """Sets the sample name (appears in acqu.par)"""
        await self.send_message(set_attribute("Sample", sample))

    async def set_data_folder(self, location: str):
        """Sets the location provided as data folder. optionally, with typeThese are included in `acq.par`"""
        if location is not None:
            self._data_folder = location
            await self.send_message(set_data_folder(location))

    async def get_user_data(self) -> dict:
        """Create a get user data request and parse result."""
        await self.send_message(get_request("UserData"))
        reply = await self._replies_by_type["GetResponse"].get()
        return {
            data_item.get("key"): data_item.get("value")
            for data_item in reply.findall(".//Data")
        }

    async def set_user_data(self, data_to_be_set: dict):
        """Set the user data provided in the dict. These are included in `acq.par`."""
        await self.send_message(set_user_data(data_to_be_set))

    async def send_message(self, root: etree.Element):
        """
        Sends the tree connected XML etree.Element provided
        """
        # Turn the etree.Element provided into an ElementTree
        tree = etree.ElementTree(root)

        # Message must include XML declaration
        message = etree.tostring(tree, xml_declaration=True, encoding="utf-8")

        logger.debug(f"Transmitting request to spectrometer: {message}")
        await self._transmit(message)

    async def hw_request(self):
        """
        Sends an HW request to the spectrometer, receive the reply and returns it
        """
        await self.send_message(create_message("HardwareRequest"))
        return await self._replies_by_type["HardwareResponse"].get()

    async def request_available_protocols(self) -> dict[str, dict]:
        """
        Get a list of available protocol on the current spectrometer
        """
        await self.send_message(create_message("AvailableProtocolOptionsRequest"))
        reply = await self._replies_by_type["AvailableProtocolOptionsResponse"].get()

        # Parse reply and construct the dict with protocols available
        protocols = {}
        for element in reply.findall(".//Protocol"):
            protocol_name = element.get("protocol")
            protocols[protocol_name] = {
                option.get("name"): [value.text for value in option.findall("Value")]
                for option in element.findall("Option")
            }
        return protocols

    async def run_protocol(
        self, protocol_name, background_tasks: BackgroundTasks, protocol_options=None
    ) -> int:
        """Run a protocol.

        Returns the ID of the protocol (needed to get folder once ready). -1 for errors.
        The validation is performed before the response is sent, the actual protocol later, as it may take a long time.
        """
        # All protocol names are UPPERCASE, so force upper here to avoid case issues
        protocol_name = protocol_name.upper()
        if not self.is_protocol_available(protocol_name):
            warnings.warn(
                f"The protocol requested '{protocol_name}' is not available on the spectrometer!\n"
                f"Valid options are: {pp.pformat(sorted(self.protocols_option.keys()))}"
            )
            return -1

        # Validate protocol options (check values and remove invalid ones, with warning)
        valid_protocol_options = self._validate_protocol_request(
            protocol_name, protocol_options
        )

        # Flush all previous StatusNotification replies from queue
        notificaiton_q = self._replies_by_type["StatusNotification"]
        for _ in range(notificaiton_q.qsize()):
            notificaiton_q.get_nowait()

        # Start protocol
        await self.send_message(
            create_protocol_message(protocol_name, valid_protocol_options)
        )

        # Rest of protocol as bg task to avoid timeout on API reply
        # See https://fastapi.tiangolo.com/tutorial/background-tasks/
        background_tasks.add_task(self._check_notifications)

        return len(self._result_folders)

    async def _check_notifications(self):
        """Read all the StatusNotification and returns the dataFolder."""
        self._protocol_running = True
        remote_folder = Path()
        while True:
            # Get all StatusNotification
            status_update = await self._replies_by_type["StatusNotification"].get()

            # Parse them
            status, folder = parse_status_notification(status_update)
            logger.debug(f"Status update: Status is {status} and data folder={folder}")

            # When I get a finishing response end protocol and return the data folder!
            if status is StatusNotification.FINISHING:
                remote_folder = Path(folder)
                break

            if status is StatusNotification.ERROR:
                # Usually device busy
                warnings.warn("Error detected on running protocol -- aborting.")
                await self.abort()  # Abort running experiment
                break

        logger.info(f"Protocol over - remote data folder is {remote_folder}")
        # If a folder mapper is present use it to translate the location
        if self._folder_mapper is not None:
            self._result_folders.append(self._folder_mapper(remote_folder))
        else:
            self._result_folders.append(remote_folder)

        self._protocol_running = False

    async def is_protocol_running(self) -> bool:
        """Return true if a protocol is currently running."""
        return self._protocol_running

    async def get_result_folder(self, result_id: int | None = None) -> str:
        """Get the result folder with the given ID or the last one if no ID is specified. Empty str if not existing."""
        # If no result_id get last
        if result_id is None:
            result_id = -1
        try:
            folder = str(self._result_folders[result_id])
        except IndexError:
            folder = ""

        return folder

    async def abort(self):
        """Abort current running command"""
        await self.send_message(create_message("Abort"))

    def is_protocol_available(self, protocol):
        """Check if the desired protocol is available on the current instrument"""
        return protocol in self.protocols_option

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

    def shim(self):
        """Shim on sample."""
        raise NotImplementedError("Use run protocol with a shimming protocol instead!")

    def get_router(self, prefix: str | None = None):
        """Spinsolve-specific route."""

        router = super().get_router(prefix)

        router.add_api_route("/solvent", self.get_solvent, methods=["GET"])
        router.add_api_route("/solvent", self.set_solvent, methods=["PUT"])

        router.add_api_route("/sample-name", self.get_sample, methods=["GET"])
        router.add_api_route("/sample-name", self.set_sample, methods=["PUT"])

        router.add_api_route("/user-data", self.get_user_data, methods=["GET"])
        router.add_api_route("/user-data", self.set_user_data, methods=["PUT"])

        router.add_api_route(
            "/protocol/is-available", self.is_protocol_available, methods=["GET"]
        )
        router.add_api_route("/protocol/run", self.run_protocol, methods=["PUT"])
        router.add_api_route(
            "/protocol/is-running", self.is_protocol_running, methods=["GET"]
        )
        router.add_api_route(
            "/protocol/get_result", self.get_result_folder, methods=["GET"]
        )
        router.add_api_route("/protocol/abort", self.abort, methods=["PUT"])

        return router


if __name__ == "__main__":
    hostname = "127.0.0.1"

    async def main():
        nmr: Spinsolve = Spinsolve(host=hostname, port=13000)
        print(nmr.sample)
        await nmr.initialize()
        s = await nmr.get_solvent()
        print(f"sovlent sis {s}")

    asyncio.run(main())
