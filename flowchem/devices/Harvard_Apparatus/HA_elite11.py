"""
This module is used to control Harvard Apparatus Elite 11 syringe pump via the 11 protocol.
"""

from __future__ import annotations

import logging
import threading
import warnings
from dataclasses import dataclass
from enum import Enum
from time import sleep
from typing import Union, List, Optional, Tuple

import aioserial
from pint import UnitRegistry

from flowchem.constants import InvalidConfiguration, DeviceError


@dataclass
class Protocol11CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """

    command_string: str
    reply_lines: int  # Reply line without considering leading newline and tailing prompt!
    requires_argument: bool

    def to_pump(self, address: int, argument: str = "") -> Protocol11Command:
        """ Returns a Protocol11Command by adding to the template pump address and command arguments """
        if self.requires_argument and not argument:
            raise DeviceError(
                f"Cannot send command {self.command_string} without an argument!"
            )
        elif self.requires_argument is False and argument:
            raise DeviceError(
                f"Cannot provide an argument to command {self.command_string}!"
            )
        return Protocol11Command(
            command_string=self.command_string,
            reply_lines=self.reply_lines,
            requires_argument=self.requires_argument,
            target_pump_address=address,
            command_argument=argument,
        )


@dataclass
class Protocol11Command(Protocol11CommandTemplate):
    """ Class representing a pump command and its expected reply """

    target_pump_address: int
    command_argument: str

    def compile(self, fast: bool = False) -> str:
        """
        Create actual command byte by prepending pump address to command.
        Fast saves some ms but do not update the display.
        """
        assert 0 <= self.target_pump_address < 99
        # end character needs to be '\r\n'. Since this command building is specific for elite 11, that should be fine
        if fast:
            return (
                str(self.target_pump_address)
                + "@"
                + self.command_string
                + " "
                + self.command_argument
                + "\r\n"
            )
        else:
            return (
                str(self.target_pump_address)
                + self.command_string
                + " "
                + self.command_argument
                + "\r\n"
            )


class PumpStatus(Enum):
    """ Possible pump statuses, as defined by the reply prompt. """

    IDLE = ":"
    INFUSING = ">"
    WITHDRAWING = "<"
    TARGET_REACHED = "T"
    STALLED = "*"


class PumpIO:
    """ Setup with serial parameters, low level IO"""

    DEFAULT_CONFIG = {
        "timeout": 0.1,
        "baudrate": 115200
    }

    # noinspection PyPep8
    def __init__(self, **config):
        # Merge default settings, including serial, with provided ones.
        configuration = dict(R4Heater.DEFAULT_CONFIG, **config)

        try:
            self._serial = aioserial.AioSerial(**configuration)
        except aioserial.SerialException as e:
            raise InvalidConfiguration(f"Cannot connect to the R4Heater on the port <{config.get('port')}>") from e

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)

    def _write(self, command: Protocol11Command):
        """ Writes a command to the pump """
        command = command.compile()
        try:
            self._serial.write(command.encode("ascii"))
        except aioserial.SerialException as e:
            raise InvalidConfiguration from e
        self.logger.debug(f"Sent {repr(command)}!")

    def _read_reply(self, command) -> List[str]:
        """ Reads the pump reply from serial communication """
        reply_string = []

        # +1 for leading newline character in reply + 1 for prompt = +2
        for line_num in range(command.reply_lines + 2):
            chunk = self._serial.readline().decode("ascii")
            self.logger.debug(f"Read line: {repr(chunk)} ")

            # Stripping newlines etc allows to skip empty lines and clean output
            chunk = chunk.strip()

            # Fix bug in pump! Some prompts, such as T*, leak in the first (usually empty) line returned after commands
            if line_num == 0:
                chunk = ""

            if chunk:
                reply_string.append(chunk)

        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    @staticmethod
    def parse_response_line(line: str) -> Tuple[int, PumpStatus, str]:
        """ Split a received line in its components: address, prompt and reply body """
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
        """ Aggregates address prompt and reply body from all the reply lines and return them """
        parsed_lines = list(map(PumpIO.parse_response_line, response))
        # noinspection PyTypeChecker
        return zip(*parsed_lines)

    @staticmethod
    def check_for_errors(last_response_line, command_sent):
        """ Further response parsing, checks for error messages """
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
        """ Reset input buffer before reading from serial. In theory not necessary if all replies are consumed... """
        try:
            self._serial.reset_input_buffer()
        except aioserial.PortNotOpenError as e:
            raise InvalidConfiguration from e

    def write_and_read_reply(
        self, command: Protocol11Command, return_parsed: bool = True
    ) -> Union[List[str], str]:
        """ Main PumpIO method. Sends a command to the pump, read the replies and returns it, optionally parsed """
        self.reset_buffer()
        self._write(command)
        response = self._read_reply(command)

        if not response:
            raise InvalidConfiguration(
                f"No response received from pump, check pump address! "
                f"(Currently set to {command.target_pump_address})"
            )

        # Parse reply
        pump_address, return_status, parsed_response = PumpIO.parse_response(response)

        # Ensures that all the replies came from the target pump (this should always be the case)
        assert all(address == command.target_pump_address for address in pump_address)

        # Ensure no stall is present (this might happen, so let's raise an Exception w/ diagnostic text)
        if PumpStatus.STALLED in return_status:
            raise DeviceError

        PumpIO.check_for_errors(last_response_line=response[-1], command_sent=command)

        return parsed_response[0] if return_parsed else response

    @property
    def name(self) -> Optional[str]:
        """ This is used to provide a nice-looking default name to pumps based on their serial connection. """
        try:
            return self._serial.name
        except AttributeError:
            return None


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
    #                             output (if pin state high or low)

    EMPTY_MESSAGE = Protocol11CommandTemplate(
        command_string=" ", reply_lines=0, requires_argument=False
    )
    GET_VERSION = Protocol11CommandTemplate(
        command_string="VER", reply_lines=1, requires_argument=False
    )

    # RUN commands (no parameters, start movement in same direction/reverse direction/infuse/withdraw respectively)
    RUN = Protocol11CommandTemplate(
        command_string="run", reply_lines=0, requires_argument=False
    )
    REVERSE_RUN = Protocol11CommandTemplate(
        command_string="rrun", reply_lines=0, requires_argument=False
    )
    INFUSE = Protocol11CommandTemplate(
        command_string="irun", reply_lines=0, requires_argument=False
    )
    WITHDRAW = Protocol11CommandTemplate(
        command_string="wrun", reply_lines=0, requires_argument=False
    )

    # STOP movement
    STOP = Protocol11CommandTemplate(
        command_string="stp", reply_lines=0, requires_argument=False
    )

    # FORCE Pump force getter and setter, see Elite11.force property for range and suggested values
    GET_FORCE = Protocol11CommandTemplate(
        command_string="FORCE", reply_lines=1, requires_argument=False
    )
    SET_FORCE = Protocol11CommandTemplate(
        command_string="FORCE", reply_lines=1, requires_argument=True
    )

    # DIAMETER Syringe diameter getter and setter, see Elite11.diameter property for range and suggested values
    SET_DIAMETER = Protocol11CommandTemplate(
        command_string="diameter", reply_lines=1, requires_argument=True
    )
    GET_DIAMETER = Protocol11CommandTemplate(
        command_string="diameter", reply_lines=1, requires_argument=False
    )

    METRICS = Protocol11CommandTemplate(
        command_string="metrics", reply_lines=20, requires_argument=False
    )
    CURRENT_MOVING_RATE = Protocol11CommandTemplate(
        command_string="crate", reply_lines=1, requires_argument=False
    )

    # RAMP Ramping commands (infuse or withdraw)
    # setter: iramp [{start rate} {start units} {end rate} {end units} {ramp time in seconds}]
    GET_INFUSE_RAMP = Protocol11CommandTemplate(
        command_string="iramp", reply_lines=1, requires_argument=False
    )
    SET_INFUSE_RAMP = Protocol11CommandTemplate(
        command_string="iramp", reply_lines=1, requires_argument=True
    )
    GET_WITHDRAW_RAMP = Protocol11CommandTemplate(
        command_string="wramp", reply_lines=1, requires_argument=False
    )
    SET_WITHDRAW_RAMP = Protocol11CommandTemplate(
        command_string="wramp", reply_lines=1, requires_argument=True
    )

    # RATE
    # returns or set rate irate [max | min | lim | {rate} {rate units}]
    GET_INFUSE_RATE = Protocol11CommandTemplate(
        command_string="irate", reply_lines=1, requires_argument=False
    )
    GET_INFUSE_RATE_LIMITS = Protocol11CommandTemplate(
        command_string="irate lim", reply_lines=1, requires_argument=False
    )
    SET_INFUSE_RATE = Protocol11CommandTemplate(
        command_string="irate", reply_lines=1, requires_argument=True
    )
    GET_WITHDRAW_RATE = Protocol11CommandTemplate(
        command_string="wrate", reply_lines=1, requires_argument=False
    )
    GET_WITHDRAW_RATE_LIMITS = Protocol11CommandTemplate(
        command_string="wrate lim", reply_lines=1, requires_argument=False
    )
    SET_WITHDRAW_RATE = Protocol11CommandTemplate(
        command_string="wrate", reply_lines=1, requires_argument=True
    )

    # GET VOLUME
    INFUSED_VOLUME = Protocol11CommandTemplate(
        command_string="ivolume", reply_lines=1, requires_argument=False
    )
    GET_SYRINGE_VOLUME = Protocol11CommandTemplate(
        command_string="svolume", reply_lines=1, requires_argument=False
    )
    SET_SYRINGE_VOLUME = Protocol11CommandTemplate(
        command_string="svolume", reply_lines=1, requires_argument=True
    )
    WITHDRAWN_VOLUME = Protocol11CommandTemplate(
        command_string="wvolume", reply_lines=1, requires_argument=False
    )

    # TARGET VOLUME
    GET_TARGET_VOLUME = Protocol11CommandTemplate(
        command_string="tvolume", reply_lines=1, requires_argument=False
    )
    SET_TARGET_VOLUME = Protocol11CommandTemplate(
        command_string="tvolume", reply_lines=1, requires_argument=True
    )

    # CLEAR VOLUME
    CLEAR_INFUSED_VOLUME = Protocol11CommandTemplate(
        command_string="civolume", reply_lines=0, requires_argument=False
    )
    CLEAR_WITHDRAWN_VOLUME = Protocol11CommandTemplate(
        command_string="cwvolume", reply_lines=0, requires_argument=False
    )
    CLEAR_INFUSED_WITHDRAWN_VOLUME = Protocol11CommandTemplate(
        command_string="cvolume", reply_lines=0, requires_argument=False
    )
    CLEAR_TARGET_VOLUME = Protocol11CommandTemplate(
        command_string="ctvolume", reply_lines=0, requires_argument=False
    )

    # GET TIME
    WITHDRAWN_TIME = Protocol11CommandTemplate(
        command_string="wtime", reply_lines=1, requires_argument=False
    )
    INFUSED_TIME = Protocol11CommandTemplate(
        command_string="itime", reply_lines=1, requires_argument=False
    )

    # TARGET TIME
    GET_TARGET_TIME = Protocol11CommandTemplate(
        command_string="ttime", reply_lines=1, requires_argument=False
    )
    SET_TARGET_TIME = Protocol11CommandTemplate(
        command_string="ttime", reply_lines=1, requires_argument=True
    )

    # CLEAR TIME
    CLEAR_INFUSED_TIME = Protocol11CommandTemplate(
        command_string="citime", reply_lines=0, requires_argument=False
    )
    CLEAR_INFUSED_WITHDRAW_TIME = Protocol11CommandTemplate(
        command_string="ctime", reply_lines=0, requires_argument=False
    )
    CLEAR_TARGET_TIME = Protocol11CommandTemplate(
        command_string="cttime", reply_lines=0, requires_argument=False
    )
    CLEAR_WITHDRAW_TIME = Protocol11CommandTemplate(
        command_string="cwtime", reply_lines=0, requires_argument=False
    )


class Elite11:
    """
    Controls Harvard Apparatus Elite11 syringe pumps.

    The same protocol (Protocol11) can be used on other HA pumps, but is untested.
    Several pumps can be daisy chained on the same serial connection, if so address 0 must be the first one.
    Read the manufacturer manual for more details.
    """

    # FIXME: move to shared location and use the same UR across different devices.
    ureg = (
        UnitRegistry()
    )  # Unit converter, defaults are fine, but it would be wise explicitly list the units needed

    # This class variable is used for daisy chains (i.e. multiple pumps on the same serial connection). Details below.
    _io_instances = set()
    # The mutable object (a set) as class variable creates a shared state across all the instances.
    # When several pumps are daisy chained on the same serial port, they need to all access the same Serial object,
    # because access to the serial port is exclusive by definition (also locking there ensure thread safe operations).
    # FYI it is a borg idiom https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html

    def __init__(
        self,
        pump_io: PumpIO,
        address: int = 0,
        name: str = None,
        diameter: float = None,
        syringe_volume: float = None,
    ):
        """Query model and version number of firmware to check pump is
        OK. Responds with a load of stuff, but the last three characters
        are the prompt XXY, where XX is the address and Y is pump status.
        The status can be one of the three: [":", ">" "<"] respectively
        when stopped, running forwards (pumping), or backwards (withdrawing).
        The prompt is used to confirm that the address is correct.
        This acts as a check to see that the pump is connected and working."""

        self.pump_io = pump_io
        Elite11._io_instances.add(self.pump_io)  # See above for details.

        self.name = f"Pump {self.pump_io.name}:{address}" if name is None else name
        self.address: int = address

        if diameter is not None:
            self.set_syringe_diameter(diameter)
        if syringe_volume is not None:
            self.set_syringe_volume(syringe_volume)
        self.volume_syringe = syringe_volume

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by PumpIO
        self.log.info(
            f"Connected to pump '{self.name}' on port {self.pump_io.name}:{address} version: {self.version()}!"
        )
        # Enable withdraw commands only on pumps that support them...
        self._withdraw_enabled = True if "I/W" in self.version() else False

        # makes sure that a 'clean' pump is initialized.
        self.clear_times()
        self.clear_volumes()

        # Assume full syringe upon start-up
        self._volume_stored = self.volume_syringe

        # Can we raise an exception as soon as self._volume_stored becomes negative?
        self._target_volume = None

        # Code for Elite11 control is not ready for prime time yet ;)
        warnings.warn("The module Elite11 is being used, which is not yet completely tested!\n"
                      "Usable with: init with syringe diameter and volume. Set target volume and rate. run.")

    @classmethod
    def from_config(cls, config):
        # Many pump can be present on the same serial port with different addresses.
        # This shared list of PumpIO objects allow shared state in a borg-inspired way, avoiding singletons
        # This is only relevant to programmatic instantiation, i.e. when from_config() is called per each pump from a
        # config file, as it is the case in the HTTP server.
        # Pump_IO() manually instantiated are not accounted for.
        pumpio = None
        for obj in Elite11._io_instances:
            if obj._serial.port == config.get("port"):
                pumpio = obj
                break

        # If not existing serial object are available for the port provided, create a new one
        if pumpio is None:
            # Remove ML600-specific keys to only have HamiltonPumpIO's kwargs
            config_for_pumpio = {k: v for k, v in config.items() if k not in ("diameter", "address", "name", "syringe_volume")}
            pumpio = PumpIO(**config_for_pumpio)

        return cls(pumpio, address=config.get("address"), name=config.get("name"), diameter=config.get("diameter"),
                   syringe_volume=config.get("syringe_volume"))

    def ensure_withdraw_is_enabled(self):
        """ To be used on methods that need withdraw capabilities """
        if not self._withdraw_enabled:
            raise DeviceError(
                "Cannot call this method with an infuse-only pump! Withdraw needed :("
            )

    def send_command_and_read_reply(
        self, command_template: Protocol11CommandTemplate, parameter="", parse=True
    ) -> Union[str, List[str]]:
        """ Sends a command based on its template and return the corresponding reply as str """
        return self.pump_io.write_and_read_reply(
            command_template.to_pump(self.address, parameter), return_parsed=parse
        )

    def bound_rate_to_pump_limits(self, rate_in_ml_min: float) -> float:
        """ Bound the rate provided to pump's limit. NOTE: Infusion and withdraw limits are equal! """
        # Get current pump limits (those are function of the syringe diameter)
        limits_raw = self.send_command_and_read_reply(
            Elite11Commands.GET_INFUSE_RATE_LIMITS
        )

        # Lower limit usually expressed in nl/min so unit-aware quantities are needed
        lower_limit, upper_limit = map(Elite11.ureg, limits_raw.split(" to "))

        # Also add units to the provided rate
        value_w_units = Elite11.ureg.Quantity(rate_in_ml_min, "ml/min")

        # Bound rate to acceptance range
        set_rate = max(lower_limit, min(upper_limit, value_w_units)).m_as("ml/min")

        # If the set rate was adjusted to fit limits warn user
        if set_rate != rate_in_ml_min:
            warnings.warn(
                f"The requested rate {rate_in_ml_min} ml/min was outside the acceptance range"
                f"[{lower_limit} - {upper_limit}] and was bounded to {set_rate} ml/min!"
            )
        return set_rate

    def version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        return self.send_command_and_read_reply(
            Elite11Commands.GET_VERSION
        )  # '11 ELITE I/W Single 3.0.4

    def get_status(self) -> PumpStatus:
        """ Empty message to trigger a new reply and evaluate connection and pump current status via reply prompt """
        return PumpStatus(
            self.send_command_and_read_reply(
                Elite11Commands.EMPTY_MESSAGE, parse=False
            )[0][2:3]
        )

    def is_moving(self) -> bool:
        """ Evaluate prompt for current status, i.e. moving or not """
        prompt = self.get_status()
        return prompt in (PumpStatus.INFUSING, PumpStatus.WITHDRAWING)

    def get_syringe_volume(self) -> float:
        """ Returns the syringe volume in ml. """
        volume_w_units = self.send_command_and_read_reply(
            Elite11Commands.GET_SYRINGE_VOLUME
        )  # e.g. '100 ml'
        return Elite11.ureg(volume_w_units).m_as(
            "ml"
        )  # Unit registry does the unit conversion and returns ml

    def set_syringe_volume(self, volume_in_ml: float = None):
        """
        Sets the syringe volume in ml.

        :param volume_in_ml: the volume of the syringe.
        """
        self.send_command_and_read_reply(
            Elite11Commands.SET_SYRINGE_VOLUME, parameter=f"{volume_in_ml} m"
        )

    def update_stored_volume(self):
        """ FIXME: write docstring and check this """
        infused = self.get_infused_volume()
        if self._withdraw_enabled:
            withdrawn = self.get_withdrawn_volume()
        else:
            withdrawn = 0
        net_volume = withdrawn - infused
        # not really nice, also the target_volume and rate should be class attributes?
        self._volume_stored += net_volume
        # clear stored i w volume
        # if withdrawn+infused != 0:
        #     self.clear_infused_withdrawn_volume()

    # TODO: when sending itime, pump will return the needed time for infusion of target volume.
    #  this could be used for time efficiency
    def run(self):
        # actually should be avoided, because in principle, this will move in any direction that it move before
        # TODO if stp while infuse/withdraw: get the infused withdrawn volume and correct
        """activates pump, runs in the previously set direction"""

        # this takes ANY volume changes before, updates internal variable and runs
        self.update_stored_volume()
        if self.is_moving():
            # should raise exception
            raise DeviceError("Pump already is moving")

        # if target volume is set, check if this is achievable
        elif (
            self._target_volume is not None
            and self._volume_stored < self._target_volume
        ):
            raise DeviceError("Pump contains less volume than required")
        else:
            self.send_command_and_read_reply(Elite11Commands.RUN)

        self.log.info("Pump started to run")

    def inverse_run(self):
        """ Activates pump, runs opposite to previously set direction. """
        self.send_command_and_read_reply(Elite11Commands.REVERSE_RUN)
        self.log.info("Pump started to run in reverse direction")

    def infuse_run(self):
        """ Activates pump, runs in infuse mode. """
        self.update_stored_volume()

        if self.is_moving():
            raise DeviceError("Pump already is moving")

        # if target volume is set, check if this is achievable
        elif self._target_volume:
            if self._volume_stored < self._target_volume:
                raise DeviceError("Pump contains less volume than required")
        else:
            self.send_command_and_read_reply(Elite11Commands.INFUSE)

        self.log.info("Pump started to infuse")

    def withdraw_run(self):
        """ Activates pump, runs in withdraw mode. """
        self.ensure_withdraw_is_enabled()
        self.update_stored_volume()

        if self.is_moving():
            raise DeviceError("Pump already is moving")

        # if target volume is set, check if this is achievable
        elif self._target_volume:
            if self._volume_stored + self._target_volume > self.volume_syringe:
                raise DeviceError("Pump would be overfilled")
        else:
            self.send_command_and_read_reply(Elite11Commands.WITHDRAW)

        self.log.info("Pump started to withdraw")

    def stop(self):
        """stops pump"""
        self.send_command_and_read_reply(Elite11Commands.STOP)
        self.update_stored_volume()

        self.log.info("Pump stopped")

    def wait_until_idle(self):
        """ Wait until the pump is no more moving """
        is_still = False
        while not is_still:
            if not self.is_moving():
                is_still = True

    def get_infusion_rate(self) -> float:
        """ Returns the infusion rate in ml*min-1 """
        rate_w_units = self.send_command_and_read_reply(
            Elite11Commands.GET_INFUSE_RATE
        )  # e.g. '0.2 ml/min'
        return Elite11.ureg(rate_w_units).m_as(
            "ml/min"
        )  # Unit registry does the unit conversion and returns ml/min

    def set_infusion_rate(self, rate_in_ml_min: float):
        """ Sets the infusion rate in ml*min-1 """
        set_rate = self.bound_rate_to_pump_limits(rate_in_ml_min=rate_in_ml_min)
        self.send_command_and_read_reply(
            Elite11Commands.SET_INFUSE_RATE, parameter=f"{set_rate:.10f} m/m"
        )

    def get_withdrawing_rate(self) -> float:
        """ Returns the infusion rate in ml*min-1 """
        self.ensure_withdraw_is_enabled()
        rate_w_units = self.send_command_and_read_reply(
            Elite11Commands.GET_WITHDRAW_RATE
        )
        return Elite11.ureg(rate_w_units).m_as(
            "ml/min"
        )  # Unit registry does the unit conversion and returns ml/min

    def set_withdrawing_rate(self, rate_in_ml_min: float):
        """ Sets the infusion rate in ml*min-1 """
        self.ensure_withdraw_is_enabled()
        set_rate = self.bound_rate_to_pump_limits(rate_in_ml_min=rate_in_ml_min)
        self.send_command_and_read_reply(
            Elite11Commands.SET_WITHDRAW_RATE, parameter=f"{set_rate} m/m"
        )

    def get_infused_volume(self) -> float:
        """ Return infused volume in ml """
        return Elite11.ureg(
            self.send_command_and_read_reply(Elite11Commands.INFUSED_VOLUME)
        ).m_as("ml")

    def get_withdrawn_volume(self):
        """ Returns the withdrawn volume from the last clear_*_volume() command, according to the pump """
        self.ensure_withdraw_is_enabled()
        return Elite11.ureg(
            self.send_command_and_read_reply(Elite11Commands.WITHDRAWN_VOLUME)
        ).m_as("ml")

    def clear_infused_volume(self):
        """ Reset the pump infused volume counter to 0 """
        self.send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_VOLUME)

    def clear_withdrawn_volume(self):
        """ Reset the pump withdrawn volume counter to 0 """
        self.ensure_withdraw_is_enabled()
        self.send_command_and_read_reply(Elite11Commands.CLEAR_WITHDRAWN_VOLUME)

    def clear_infused_withdrawn_volume(self):
        """ Reset both the pump infused and withdrawn volume counters to 0 """
        self.ensure_withdraw_is_enabled()
        self.send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_WITHDRAWN_VOLUME)
        sleep(0.1)  # FIXME check if needed

    def clear_volumes(self):
        """ Set all pump volumes to 0 """
        self.target_volume = 0
        self._target_volume = None
        if self._withdraw_enabled:
            self.clear_infused_withdrawn_volume()
        else:
            self.clear_infused_volume()

    def get_force(self):
        """
        Pump force, in percentage.
        Manufacturer suggested values are:
            stainless steel:    100%
            plastic syringes:   50% if volume <= 5 ml else 100%
            glass/glass:        30% if volume <= 20 ml else 50%
            glass/plastic:      30% if volume <= 250 ul, 50% if volume <= 5ml else 100%
        """
        return int(self.send_command_and_read_reply(Elite11Commands.GET_FORCE)[:-1])

    def set_force(self, force_percent: int):
        self.send_command_and_read_reply(
            Elite11Commands.SET_FORCE, parameter=str(int(force_percent))
        )

    def get_syringe_diameter(self) -> float:
        """
        Syringe diameter in mm. This can be set in the interval 1 mm to 33 mm
        """
        return self.syringe_diameter

    def set_syringe_diameter(self, diameter_in_mm: float):
        warnings.warn(
            "Deprecated property, use more explicit syringe_diameter instead!",
            FutureWarning,
        )
        self.syringe_diameter = diameter_in_mm

    def get_current_flowrate(self):
        """
        If pump moves, this returns the current moving rate. If not running None.
        :return: current moving rate
        """
        if self.is_moving():
            return self.send_command_and_read_reply(Elite11Commands.CURRENT_MOVING_RATE)
        else:
            warnings.warn("Pump is not moving, cannot provide moving rate!")
            return None

    def get_target_volume(self) -> float:
        """
        Set/returns target volume in ml. If the volume is set to 0, the target is cleared.
        """
        target_volume = Elite11.ureg(
            self.send_command_and_read_reply(Elite11Commands.GET_TARGET_VOLUME)
        )
        return target_volume.m_as("ml")

    def set_target_volume(self, target_volume_in_ml: float):
        if target_volume_in_ml == 0:
            self.send_command_and_read_reply(Elite11Commands.CLEAR_TARGET_VOLUME)
        else:
            self.send_command_and_read_reply(
                Elite11Commands.SET_TARGET_VOLUME, parameter=f"{target_volume_in_ml} m"
            )

    def clear_times(self):
        """ Clear all pump measured times (i.e. infused and withdrawn) """
        if self._withdraw_enabled:
            self.send_command_and_read_reply(
                Elite11Commands.CLEAR_INFUSED_WITHDRAW_TIME
            )
        else:
            self.send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_TIME)
        self.send_command_and_read_reply(Elite11Commands.CLEAR_TARGET_TIME)

    @property
    def metrics(self):
        """ Returns many info :D  FIXME check this and improve docstring """
        non_parsed_reply: List[str] = self.send_command_and_read_reply(
            Elite11Commands.METRICS, parse=False
        )
        _, _, parsed_multiline_response = PumpIO.parse_response(non_parsed_reply)
        return parsed_multiline_response

    def get_router(self):
        """ Creates an APIRouter for this object. """
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/parameters/syringe-volume", self.get_syringe_volume, methods=["GET"])
        router.add_api_route("/parameters/syringe-volume", self.set_syringe_volume, methods=["PUT"])
        router.add_api_route("/parameters/force", self.get_force, methods=["PUT"])
        router.add_api_route("/parameters/force", self.set_force, methods=["PUT"])
        router.add_api_route("/run", self.run, methods=["PUT"])
        router.add_api_route("/run/inverse", self.inverse_run, methods=["PUT"])
        router.add_api_route("/run/infuse", self.infuse_run, methods=["PUT"])
        router.add_api_route("/run/withdraw", self.withdraw_run, methods=["PUT"])
        router.add_api_route("/stop", self.stop, methods=["PUT"])
        router.add_api_route("/infusion-rate", self.get_infusion_rate, methods=["GET"])
        router.add_api_route("/infusion-rate", self.set_infusion_rate, methods=["PUT"])
        router.add_api_route("/withdraw-rate", self.get_withdrawing_rate, methods=["GET"])
        router.add_api_route("/withdraw-rate", self.set_withdrawing_rate, methods=["PUT"])
        router.add_api_route("/info/version", self.version, methods=["GET"])
        router.add_api_route("/info/status", self.get_status, methods=["GET"], response_model=PumpStatus)  # CHECK THIS!
        router.add_api_route("/info/is-moving", self.is_moving, methods=["GET"])
        router.add_api_route("/info/current-flowrate", self.get_current_flowrate, methods=["GET"])
        router.add_api_route("/info/infused-volume", self.get_infused_volume, methods=["GET"])
        router.add_api_route("/info/reset-infused-volume", self.clear_infused_volume, methods=["PUT"])
        router.add_api_route("/info/withdrawn-volume", self.get_withdrawn_volume, methods=["GET"])
        router.add_api_route("/info/reset-withdrawn", self.clear_withdrawn_volume, methods=["PUT"])
        router.add_api_route("/info/reset-all", self.clear_volumes, methods=["GET"])

        return router


# TARGET VOLuME AND TIME ARE THE THINGS TO USE!!! Rate needs to be set, infuse or withdraw, then simply start!


"""
TODO:
    - T* should be included, and ensure that an object can be initialized from graph-provided info
    - if pump in isn't in quick start mode: reply is command error Non system commands bla bla so this is caught,
    maybe get more explanatory logging message
    - tests?
"""


if __name__ == "__main__":
    # from flowchem.devices.Harvard_Apparatus.HA_elite11 import *
    # import logging
    logging.basicConfig()
    logging.getLogger("flowchem").setLevel(logging.DEBUG)

    a = PumpIO(6)
    p = Elite11(a, 9)
