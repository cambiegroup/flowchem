"""
This module is used to control Harvard Apparatus Elite 11 syringe pump via the 11 protocol.
"""

from __future__ import annotations
from typing import Set, Optional, List, Tuple
from loguru import logger

import asyncio
import warnings
from dataclasses import dataclass
from enum import Enum
from time import sleep

import aioserial
from pydantic import BaseModel

from flowchem.exceptions import InvalidConfiguration, DeviceError
from flowchem.units import flowchem_ureg
from flowchem.components.stdlib import Pump


class PumpInfo(BaseModel):
    """
    Detailed pump info.
    """

    pump_type: str
    pump_description: str
    infuse_only: bool

    # noinspection PyUnboundLocalVariable
    @classmethod
    def parse_pumpstring(cls, metrics_text: List[str]):
        """Parse pump response string into model."""
        for line in metrics_text:
            if line.startswith("Pump type  "):
                pump_type = line[9:].strip()
            if line.startswith("Pump type string"):
                pump_description = line[16:].strip()
            if line.startswith("Direction"):
                if "withdraw" in line:
                    infuse_only = False
                else:
                    infuse_only = True
        return cls(
            pump_type=pump_type,
            pump_description=pump_description,
            infuse_only=infuse_only,
        )


@dataclass
class Protocol11Command:
    """Class representing a pump command and its expected reply"""

    command_string: str
    target_pump_address: int
    command_argument: str

    def compile(self) -> str:
        """
        Create actual command byte by prepending pump address to command.
        """
        assert 0 <= self.target_pump_address < 99
        return (
            str(self.target_pump_address)
            + self.command_string
            + " "
            + self.command_argument
            + "\r\n"
        )


class PumpStatus(Enum):
    """Possible pump statuses, as defined by the reply prompt."""

    IDLE = ":"
    INFUSING = ">"
    WITHDRAWING = "<"
    TARGET_REACHED = "T"
    STALLED = "*"


class HarvardApparatusPumpIO:
    """Setup with serial parameters, low level IO"""

    DEFAULT_CONFIG = {"timeout": 0.1, "baudrate": 115200}

    # noinspection PyPep8
    def __init__(self, port: str, **kwargs):
        # Merge default settings, including serial, with provided ones.
        configuration = dict(HarvardApparatusPumpIO.DEFAULT_CONFIG, **kwargs)

        try:
            self._serial = aioserial.AioSerial(port, **configuration)
        except aioserial.SerialException as e:
            raise InvalidConfiguration(
                f"Cannot connect to the Pump on the port <{port}>"
            ) from e

    async def _write(self, command: Protocol11Command):
        """Writes a command to the pump"""
        command_msg = command.compile()
        try:
            await self._serial.write_async(command_msg.encode("ascii"))
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e
        logger.debug(f"Sent {repr(command_msg)}!")

    async def _read_reply(self) -> List[str]:
        """Reads the pump reply from serial communication"""
        reply_string = []

        for line in await self._serial.readlines_async():
            reply_string.append(line.decode("ascii").strip())
            logger.debug(f"Received {repr(line)}!")

        # First line is usually empty, but some prompts such as T* actually leak into this line sometimes.
        reply_string.pop(0)

        # remove empty strings from reply_string
        reply_string = [x for x in reply_string if x]

        return reply_string

    @staticmethod
    def parse_response_line(line: str) -> Tuple[int, PumpStatus, str]:
        """Split a received line in its components: address, prompt and reply body"""
        assert len(line) >= 3
        pump_address = int(line[0:2])
        status = PumpStatus(line[2:3])

        # Target reached is the only two-character status
        if status is PumpStatus.TARGET_REACHED:
            return pump_address, status, line[4:]
        else:
            return pump_address, status, line[3:]

    @staticmethod
    def parse_response(
        response: List[str],
    ) -> Tuple[List[int], List[PumpStatus], List[str]]:
        """Aggregates address prompt and reply body from all the reply lines and return them."""
        parsed_lines = list(map(HarvardApparatusPumpIO.parse_response_line, response))
        # noinspection PyTypeChecker
        return zip(*parsed_lines)  # type: ignore

    @staticmethod
    def check_for_errors(last_response_line, command_sent):
        """Further response parsing, checks for error messages"""
        if "Command error" in last_response_line:
            raise DeviceError(
                f"The command {command_sent} is invalid for pump {command_sent.target_pump_address}!"
                f"[Reply: {last_response_line}]"
            )
        elif "Unknown command" in last_response_line:
            raise DeviceError(
                f"The command {command_sent} is unknown to pump {command_sent.target_pump_address}!"
                f"[Maybe a withdraw command has been used with an infuse only pump?]"
                f"[Reply: {last_response_line}]"
            )
        elif "Argument error" in last_response_line:
            raise DeviceError(
                f"The command {command_sent} to pump {command_sent.target_pump_address} has an "
                f"invalid argument [Reply: {last_response_line}]"
            )
        elif "Out of range" in last_response_line:
            raise DeviceError(
                f"The command {command_sent} to pump {command_sent.target_pump_address} has an "
                f"argument out of range! [Reply: {last_response_line}]"
            )

    def reset_buffer(self):
        """Reset input buffer before reading from serial. In theory not necessary if all replies are consumed..."""
        try:
            self._serial.reset_input_buffer()
        except aioserial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    async def write_and_read_reply(
        self, command: Protocol11Command, return_parsed: bool = True
    ) -> List[str]:
        """Main PumpIO method. Sends a command to the pump, read the replies and returns it, optionally parsed.

        If unparsed reply is a List[str] with raw replies.
        If parsed reply is a List[str] w/ reply body (address and prompt removed from each line)"""
        self.reset_buffer()
        await self._write(command)
        response = await self._read_reply()

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command.target_pump_address})"
            )

        # Parse reply
        (
            pump_address,
            return_status,
            parsed_response,
        ) = HarvardApparatusPumpIO.parse_response(response)

        # Ensures that all the replies came from the target pump (this should always be the case)
        assert all(address == command.target_pump_address for address in pump_address)

        # Ensure no stall is present (this might happen, so let's raise an Exception w/ diagnostic text)
        if PumpStatus.STALLED in return_status:
            raise DeviceError("Pump stalled! Press display on pump to clear error :(")

        HarvardApparatusPumpIO.check_for_errors(
            last_response_line=response[-1], command_sent=command
        )

        return parsed_response if return_parsed else response

    @property
    def name(self) -> Optional[str]:
        """This is used to provide a nice-looking default name to pumps based on their serial connection."""
        try:
            return self._serial.name
        except AttributeError:
            return None

    def autodetermine_address(self) -> int:
        self._serial.write("\r\n".encode("ascii"))
        self._serial.readline()
        prompt = self._serial.readline()
        address = 0 if prompt[0:2] == b":" else int(prompt[0:2])
        logger.debug(f"Address autodetected as {address}")
        return address


# noinspection SpellCheckingInspection
class Elite11Commands:

    """Holds the commands and arguments. Nota bene: Pump needs to be in Quick Start mode, which can be achieved from
    the display interface"""

    # collected commands
    # Methods can be programmed onto the pump and their execution remotely triggered.
    # No support is provided to such feature as "explicit is better than implicit", i.e. the same result can be obtained
    # with a sequence of Elite11Commands, with the advantage of ensuring code reproducibility (i.e. no specific
    # configuration is needed on the pump side)
    #
    # Other methods not included: dim display, usb echo, footswitch, poll, version (verbose ver), input,
    #                             output (if pin state high or low) and time commands

    EMPTY_MESSAGE = " "
    VERSION = "VER"

    # RUN commands (no parameters, start movement in same direction/reverse direction/infuse/withdraw respectively)
    RUN = "run"
    REVERSE_RUN = "rrun"
    INFUSE = "irun"
    WITHDRAW = "wrun"

    # STOP movement
    STOP = "stp"

    # Max applied force (in percent)
    FORCE = "FORCE"

    # Syringe diameter
    DIAMETER = "diameter"

    METRICS = "metrics"
    CURRENT_MOVING_RATE = "crate"

    # RAMP Ramping commands (infuse or withdraw)
    # setter: iramp [{start rate} {start units} {end rate} {end units} {ramp time in seconds}]
    INFUSE_RAMP = "iramp"
    GET_WITHDRAW_RAMP = "wramp"

    # RATE
    # returns or set rate irate [max | min | lim | {rate} {rate units}]
    INFUSE_RATE = "irate"
    INFUSE_RATE_LIMITS = "irate lim"
    WITHDRAW_RATE = "wrate"
    WITHDRAW_RATE_LIMITS = "wrate lim"

    # VOLUME
    SYRINGE_VOLUME = "svolume"
    INFUSED_VOLUME = "ivolume"
    WITHDRAWN_VOLUME = "wvolume"
    TARGET_VOLUME = "tvolume"

    # CLEAR VOLUME
    CLEAR_INFUSED_VOLUME = "civolume"
    CLEAR_WITHDRAWN_VOLUME = "cwvolume"
    CLEAR_INFUSED_WITHDRAWN_VOLUME = "cvolume"
    CLEAR_TARGET_VOLUME = "ctvolume"


# noinspection PyProtectedMember
class Elite11InfuseOnly(Pump):
    """
    Controls Harvard Apparatus Elite11 syringe pumps.

    The same protocol (Protocol11) can be used on other HA pumps, but is untested.
    Several pumps can be daisy chained on the same serial connection, if so address 0 must be the first one.
    Read the manufacturer manual for more details.
    """

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances: Set[HarvardApparatusPumpIO] = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).
    # FYI it is a borg idiom https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html

    metadata = {
        "author": [
            {
                "first_name": "Jakob",
                "last_name": "Wolf",
                "email": "jakob.wolf@mpikg.mpg.de",
                "institution": "Max Planck Institute of Colloids and Interfaces",
                "github_username": "JB-Wolf",
            },
            {
                "first_name": "Dario",
                "last_name": "Cambie",
                "email": "dario.cambie@mpikg.mpg.de",
                "institution": "Max Planck Institute of Colloids and Interfaces",
                "github_username": "dcambie",
            },
        ],
        "stability": "beta",
        "supported": True,
    }

    def __init__(self, pump_io: HarvardApparatusPumpIO, diameter: str, syringe_volume: str,
                 address: Optional[int] = None, name: Optional[str] = None):
        """Query model and version number of firmware to check pump is
        OK. Responds with a load of stuff, but the last three characters
        are the prompt XXY, where XX is the address and Y is pump status.
        The status can be one of the three: [":", ">" "<"] respectively
        when stopped, running forwards (pumping), or backwards (withdrawing).
        The prompt is used to confirm that the address is correct.
        This acts as a check to see that the pump is connected and working."""

        self.name = f"Pump {pump_io.name}:{address}" if name is None else name
        super().__init__(name)

        self.pump_io = pump_io
        Elite11InfuseOnly._io_instances.add(self.pump_io)  # See above for details.

        self.address: int = address if address else None  # type: ignore
        self._version = None  # Set in initialize

        # diameter and syringe volume - these will be set in initialize() - check values here though.
        if diameter is None:
            raise InvalidConfiguration(
                "Please provide the syringe diameter explicitly!\nThis prevents errors :)"
            )
        else:
            self._diameter = diameter

        if syringe_volume is None:
            raise InvalidConfiguration(
                "Please provide the syringe volume explicitly!\nThis prevents errors :)"
            )
        else:
            self._syringe_volume = syringe_volume

    @classmethod
    def from_config(
        cls,
        port: str,
        diameter: str,
        syringe_volume: str,
        address: int = None,
        name: str = None,
        **serial_kwargs,
    ):
        """Programmatic instantiation from configuration

        Many pump can be present on the same serial port with different addresses.
        This shared list of PumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        config file, as it is the case in the HTTP server.
        Pump_IO() manually instantiated are not accounted for.
        """
        pumpio = None
        for obj in Elite11InfuseOnly._io_instances:
            if obj._serial.port == port:
                pumpio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if pumpio is None:
            pumpio = HarvardApparatusPumpIO(port, **serial_kwargs)

        return cls(
            pumpio,
            address=address,
            name=name,
            diameter=diameter,
            syringe_volume=syringe_volume,
        )

    async def initialize(self):
        """Ensure a valid connection with the pump has been established and sets parameters."""
        # Autodetect address if none provided
        if self.address is None:
            self.address = self.pump_io.autodetermine_address()

        await self.stop()

        await self.set_syringe_diameter(self._diameter)
        await self.set_syringe_volume(self._syringe_volume)

        logger.info(
            f"Connected to pump '{self.name}' on port {self.pump_io.name}:{self.address}!"
        )

        # makes sure that a 'clean' pump is initialized.
        self._version = self._parse_version(await self.version())

        if self._version[0] >= 3:
            await self.clear_volumes()

    async def _send_command_and_read_reply(
        self, command: str, parameter="", parse=True
    ) -> str:
        """Sends a command based on its template and return the corresponding reply as str"""

        cmd = Protocol11Command(
            command_string=command,
            target_pump_address=self.address,
            command_argument=parameter,
        )
        reply = await self.pump_io.write_and_read_reply(cmd, return_parsed=parse)
        return reply[0]

    async def _send_command_and_read_reply_multiline(
        self, command: str, parameter="", parse=True
    ) -> List[str]:
        """Sends a command based on its template and return the corresponding reply as str"""

        cmd = Protocol11Command(
            command_string=command,
            target_pump_address=self.address,
            command_argument=parameter,
        )
        return await self.pump_io.write_and_read_reply(cmd, return_parsed=parse)

    async def _bound_rate_to_pump_limits(self, rate: str) -> float:
        """Bound the rate provided to pump's limit. These are function of the syringe diameter.

        NOTE: Infusion and withdraw limits are equal!"""
        # Get current pump limits (those are function of the syringe diameter)
        limits_raw = await self._send_command_and_read_reply(
            Elite11Commands.INFUSE_RATE_LIMITS
        )

        # Lower limit usually expressed in nl/min so unit-aware quantities are needed
        lower_limit, upper_limit = map(flowchem_ureg, limits_raw.split(" to "))

        # Also add units to the provided rate
        set_rate = flowchem_ureg(rate)

        # Bound rate to acceptance range
        if set_rate < lower_limit:
            warnings.warn(
                f"The requested rate {rate} is lower than the minimum possible ({lower_limit})!"
                f"Setting rate to {lower_limit} instead!"
            )
            set_rate = lower_limit

        if set_rate > upper_limit:
            warnings.warn(
                f"The requested rate {rate} is higher than the maximum possible ({upper_limit})!"
                f"Setting rate to {upper_limit} instead!"
            )
            set_rate = upper_limit

        return set_rate.to("ml/min").magnitude

    def _parse_version(self, version_text: str) -> Tuple[int, int, int]:
        """Extract semver from version string"""

        numbers = version_text.split(" ")[-1]
        version_digits = numbers.split(".")
        return int(version_digits[0]), int(version_digits[1]), int(version_digits[2])

    async def version(self) -> str:
        """Returns the current firmware version reported by the pump"""
        return await self._send_command_and_read_reply(
            Elite11Commands.VERSION
        )  # '11 ELITE I/W Single 3.0.4

    async def get_status(self) -> PumpStatus:
        """Empty message to trigger a new reply and evaluate connection and pump current status via reply prompt"""
        status = await self._send_command_and_read_reply(
            Elite11Commands.EMPTY_MESSAGE, parse=False
        )
        return PumpStatus(status[2:3])

    async def is_moving(self) -> bool:
        """Evaluate prompt for current status, i.e. moving or not"""
        prompt = await self.get_status()
        return prompt in (PumpStatus.INFUSING, PumpStatus.WITHDRAWING)

    async def is_idle(self) -> bool:
        """Returns true if idle."""
        return not await self.is_moving()

    async def get_syringe_volume(self) -> str:
        """Returns the syringe volume as str w/ units."""
        return await self._send_command_and_read_reply(
            Elite11Commands.SYRINGE_VOLUME
        )  # e.g. '100 ml'

    async def set_syringe_volume(self, volume_w_units: str = None):
        """Sets the syringe volume in ml.

        :param volume: the volume of the syringe.
        """
        volume = flowchem_ureg(volume_w_units)
        await self._send_command_and_read_reply(
            Elite11Commands.SYRINGE_VOLUME, parameter=f"{volume.m_as('ml'):.15f} m"
        )

    async def run(self):
        """Activates pump, runs in the previously set direction."""

        if await self.is_moving():
            warnings.warn("Cannot start pump: already moving!")
            return

        await self._send_command_and_read_reply(Elite11Commands.RUN)
        logger.info("Pump movement started! (direction unspecified)")

    async def infuse_run(self):
        """Activates pump, runs in infuse mode."""
        if await self.is_moving():
            warnings.warn("Cannot start pump: already moving!")
            return

        await self._send_command_and_read_reply(Elite11Commands.INFUSE)
        logger.info("Pump movement started in infuse direction!")

    async def stop(self):
        """stops pump"""
        await self._send_command_and_read_reply(Elite11Commands.STOP)
        logger.info("Pump stopped")

    async def wait_until_idle(self):
        """Wait until the pump is no more moving"""
        while await self.is_moving():
            await asyncio.sleep(0.05)

    async def get_infusion_rate(self) -> str:
        """Returns the infusion rate as str w/ units"""
        return await self._send_command_and_read_reply(
            Elite11Commands.INFUSE_RATE
        )  # e.g. '0.2 ml/min'

    async def set_infusion_rate(self, rate: str):
        """Sets the infusion rate"""
        set_rate = await self._bound_rate_to_pump_limits(rate=rate)
        await self._send_command_and_read_reply(
            Elite11Commands.INFUSE_RATE, parameter=f"{set_rate:.10f} m/m"
        )

    async def get_infused_volume(self) -> str:
        """Return infused volume as string w/ units"""
        return await self._send_command_and_read_reply(Elite11Commands.INFUSED_VOLUME)

    async def clear_infused_volume(self):
        """Reset the pump infused volume counter to 0"""
        if self._version[0] < 3:
            warnings.warn("Command not supported by pump, update firmware!")
            return
        await self._send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_VOLUME)

    async def clear_infused_withdrawn_volume(self):
        """Reset both the pump infused and withdrawn volume counters to 0"""
        self.ensure_withdraw_is_enabled()
        if self._version[0] < 3:
            warnings.warn("Command not supported by pump, update firmware!")
            return
        await self._send_command_and_read_reply(
            Elite11Commands.CLEAR_INFUSED_WITHDRAWN_VOLUME
        )
        sleep(0.1)  # FIXME check if needed

    async def clear_volumes(self):
        """Set all pump volumes to 0"""
        await self.set_target_volume(0)
        await self.clear_infused_volume()

    async def get_force(self):
        """
        Pump force, in percentage.
        Manufacturer suggested values are:
            stainless steel:    100%
            plastic syringes:   50% if volume <= 5 ml else 100%
            glass/glass:        30% if volume <= 20 ml else 50%
            glass/plastic:      30% if volume <= 250 ul, 50% if volume <= 5ml else 100%
        """
        percent = await self._send_command_and_read_reply(Elite11Commands.FORCE)
        return int(percent[:-1])

    async def set_force(self, force_percent: float):
        """Sets the pump force, see `Elite11.get_force()` for suggested values."""
        await self._send_command_and_read_reply(
            Elite11Commands.FORCE, parameter=str(int(force_percent))
        )

    async def get_syringe_diameter(self) -> str:
        """Syringe diameter in mm. This can be set in the interval 1 mm to 33 mm"""
        return await self._send_command_and_read_reply(Elite11Commands.DIAMETER)

    async def set_syringe_diameter(self, diameter_w_units: str):
        """
        Set syringe diameter. This can be set in the interval 1 mm to 33 mm
        """
        diameter = flowchem_ureg(diameter_w_units)
        if not 1 * flowchem_ureg.mm <= diameter <= 33 * flowchem_ureg.mm:
            warnings.warn(
                f"Diameter provided ({diameter}) is not valid, ignored! [Accepted range: 1-33 mm]"
            )
            return

        await self._send_command_and_read_reply(
            Elite11Commands.DIAMETER, parameter=f"{diameter.to('mm'):.4f}"
        )

    async def get_current_flowrate(self) -> str:
        """
        If pump moves, this returns the current moving rate. If not running empty string.
        :return: current moving rate
        """
        if await self.is_moving():
            return await self._send_command_and_read_reply(
                Elite11Commands.CURRENT_MOVING_RATE
            )
        else:
            warnings.warn("Pump is not moving, cannot provide moving rate!")
            return ""

    async def get_target_volume(self) -> str:
        """Returns target volume or a falsy empty string if not set."""

        target_vol = await self._send_command_and_read_reply(
            Elite11Commands.TARGET_VOLUME
        )
        if "Target volume not set" in target_vol:
            return ""
        return target_vol

    async def set_target_volume(self, volume: str):
        """
        Sets target volume in ml. If the volume is set to 0, the target is cleared.
        """
        target_volume = flowchem_ureg(volume)
        if target_volume.magnitude == 0:
            await self._send_command_and_read_reply(Elite11Commands.CLEAR_TARGET_VOLUME)
        else:
            set_vol = await self._send_command_and_read_reply(
                Elite11Commands.TARGET_VOLUME,
                parameter=f"{target_volume.m_as('ml')} m",
            )
            if "Argument error" in set_vol:
                warnings.warn(
                    f"Cannot set target volume of {target_volume} with a "
                    f"{self.get_syringe_volume()} syringe!"
                )

    async def pump_info(self) -> PumpInfo:
        """Returns many info

        e.g.
        ('Pump type          Pump 11',
        'Pump type string   11 ELITE I/W Single',
        'Display type       Sharp',
        'Steps per rev      400',
        'Gear ratio         1:1',
        'Pulley ratio       2.4:1',
        'Lead screw         24 threads per inch',
        'Microstepping      16 microsteps per step',
        'Low speed limit    27 seconds',
        'High speed limit   26 microseconds',
        'Motor polarity     Reverse',
        'Min syringe size   0.1 mm',
        'Max syringe size   33 mm',
        'Min raw force %    20%',
        'Max raw force %    80%',
        'Encoder            100 lines',
        'Direction          Infuse/withdraw',
        'Programmable       Yes',
        'Limit switches     No',
        'Command set        None', '')
        """
        parsed_multiline_response = await self._send_command_and_read_reply_multiline(
            Elite11Commands.METRICS
        )
        return PumpInfo.parse_pumpstring(parsed_multiline_response)

    def get_router(self):
        """Creates an APIRouter for this object."""
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route(
            "/parameters/syringe-volume", self.get_syringe_volume, methods=["GET"]
        )
        router.add_api_route(
            "/parameters/syringe-volume", self.set_syringe_volume, methods=["PUT"]
        )
        router.add_api_route("/parameters/force", self.get_force, methods=["PUT"])
        router.add_api_route("/parameters/force", self.set_force, methods=["PUT"])
        router.add_api_route("/run", self.run, methods=["PUT"])
        router.add_api_route("/run/infuse", self.infuse_run, methods=["PUT"])
        router.add_api_route("/stop", self.stop, methods=["PUT"])
        router.add_api_route("/infusion-rate", self.get_infusion_rate, methods=["GET"])
        router.add_api_route("/infusion-rate", self.set_infusion_rate, methods=["PUT"])
        router.add_api_route("/info/version", self.version, methods=["GET"])
        router.add_api_route(
            "/info/status", self.get_status, methods=["GET"], response_model=PumpStatus
        )
        router.add_api_route("/info/is-moving", self.is_moving, methods=["GET"])
        router.add_api_route(
            "/info/current-flowrate", self.get_current_flowrate, methods=["GET"]
        )
        router.add_api_route(
            "/info/infused-volume", self.get_infused_volume, methods=["GET"]
        )
        router.add_api_route(
            "/info/reset-infused-volume", self.clear_infused_volume, methods=["PUT"]
        )
        router.add_api_route("/info/reset-all", self.clear_volumes, methods=["GET"])

        return router


# noinspection PyProtectedMember
class Elite11InfuseWithdraw(Elite11InfuseOnly):
    """
    Controls Harvard Apparatus Elite11 syringe pumps - INFUSE AND WITHDRAW.
    """

    def __init__(self, pump_io: HarvardApparatusPumpIO, diameter: str, syringe_volume: str,
                 address: Optional[int] = None, name: Optional[str] = None):
        """Query model and version number of firmware to check pump is
        OK. Responds with a load of stuff, but the last three characters
        are the prompt XXY, where XX is the address and Y is pump status.
        The status can be one of the three: [":", ">" "<"] respectively
        when stopped, running forwards (pumping), or backwards (withdrawing).
        The prompt is used to confirm that the address is correct.
        This acts as a check to see that the pump is connected and working."""

        super().__init__(pump_io, diameter, syringe_volume, address, name)

    async def initialize(self):
        """Ensure a valid connection with the pump has been established and sets parameters."""
        await super(Elite11InfuseWithdraw, self).initialize()

        # Additionally, ensure pump support withdrawing upon initialization
        pump_info = await self.pump_info()
        assert not pump_info.infuse_only

    async def inverse_run(self):
        """Activates pump, runs opposite to previously set direction."""
        if await self.is_moving():
            warnings.warn("Cannot start pump: already moving!")
            return

        await self._send_command_and_read_reply(Elite11Commands.REVERSE_RUN)
        logger.info("Pump movement started in reverse direction!")

    async def withdraw_run(self):
        """Activates pump, runs in withdraw mode."""
        if await self.is_moving():
            warnings.warn("Cannot start pump: already moving!")
            return

        await self._send_command_and_read_reply(Elite11Commands.WITHDRAW)

        logger.info("Pump movement started in withdraw direction!")

    async def get_withdraw_rate(self) -> str:
        """Returns the infusion rate as a string w/ units"""
        return await self._send_command_and_read_reply(Elite11Commands.WITHDRAW_RATE)

    async def set_withdraw_rate(self, rate: str):
        """Sets the infusion rate"""
        set_rate = await self._bound_rate_to_pump_limits(rate=rate)
        await self._send_command_and_read_reply(
            Elite11Commands.WITHDRAW_RATE, parameter=f"{set_rate} m/m"
        )

    async def get_withdrawn_volume(self) -> str:
        """Returns the withdrawn volume from the last clear_*_volume() command, according to the pump"""
        return await self._send_command_and_read_reply(Elite11Commands.WITHDRAWN_VOLUME)

    async def clear_withdrawn_volume(self):
        """Reset the pump withdrawn volume counter to 0"""
        await self._send_command_and_read_reply(Elite11Commands.CLEAR_WITHDRAWN_VOLUME)

    async def clear_volumes(self):
        """Set all pump volumes to 0"""
        await self.set_target_volume(0)
        await self.clear_infused_volume()
        await self.clear_withdrawn_volume()

    def get_router(self):
        router = super(Elite11InfuseWithdraw, self).get_router()
        """Creates an APIRouter for this object."""
        router.add_api_route("/run/inverse", self.inverse_run, methods=["PUT"])
        router.add_api_route("/run/withdraw", self.withdraw_run, methods=["PUT"])
        router.add_api_route("/withdraw-rate", self.get_withdraw_rate, methods=["GET"])
        router.add_api_route("/withdraw-rate", self.set_withdraw_rate, methods=["PUT"])
        router.add_api_route(
            "/info/withdrawn-volume", self.get_withdrawn_volume, methods=["GET"]
        )
        router.add_api_route(
            "/info/reset-withdrawn", self.clear_withdrawn_volume, methods=["PUT"]
        )

        return router

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()

    async def _update(self):
        """Actuates flow rate changes."""
        if self.rate == 0:
            await self.stop()
        else:
            await self.set_infusion_rate(str(self.rate))
            await self.infuse_run()


if __name__ == "__main__":
    pump = Elite11InfuseOnly.from_config(port="COM4", syringe_volume="10 ml", diameter="10 mm")

    async def main():
        """Test function"""
        await pump.initialize()
        # assert await pump.get_infused_volume() == 0
        await pump.set_syringe_diameter("30 mm")
        await pump.set_infusion_rate("0.1 ml/min")
        await pump.set_target_volume("0.05 ml")
        await pump.infuse_run()
        await asyncio.sleep(2)
        await pump.pump_info()

    asyncio.run(main())
