from __future__ import annotations

import logging
import threading
from typing import Union, List, TypedDict, Optional
from dataclasses import dataclass
from tenacity import retry, retry_if_exception_type, stop_after_attempt

import serial


class Elite11Exception(Exception):
    pass


class InvalidConfiguration(Elite11Exception):
    pass


class NotConnectedError(Elite11Exception):
    pass


class CommandNotSupported(Elite11Exception):
    pass


class InvalidReply(Elite11Exception):
    pass


class ArgumentNotSupported(Elite11Exception):
    pass

class UnachievableMove(Elite11Exception):
    pass

class Elite11PumpConfiguration(TypedDict):
    pass


@dataclass
class Protocol11CommandTemplate:
    """ Class representing a pump command and its expected reply, but without target pump number """
    command_string: str
    reply_lines: int

    def to_pump(self, address: int, argument: str = '') -> Protocol11Command:
        return Protocol11Command(command_string=self.command_string, reply_lines=self.reply_lines,
                                 target_pump_address=address, command_argument=argument)




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
            msg =str(self.target_pump_address) + "@" + self.command_string + ' ' + self.command_argument + "\r\n"
        else:
            msg = str(self.target_pump_address) + self.command_string + ' ' + self.command_argument + "\r\n"
        return msg

class PumpIO:
    """ Setup with serial parameters, low level IO"""
    VALID_PROMPTS = (":", ">", "<", "T")

    def __init__(self, port: str, baud_rate: int = 115200):
        if baud_rate not in serial.serialutil.SerialBase.BAUDRATES:
            raise InvalidConfiguration(f"Invalid baud rate provided {baud_rate}!")

        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.lock = threading.Lock()

        self._serial = serial.Serial(port=port,baudrate=baud_rate, bytesize=serial.EIGHTBITS,
                                     parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=1,
                                     xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False,
                                     exclusive=None)  # type:Union[serial.serialposix.Serial, serial.serialwin32.Serial]

    def _write(self, command: Protocol11Command):
        """ Writes a command to the pump """
        command = command.compile(fast=False)
        self.logger.debug(f"Sending {command}")
        try:
            self._serial.write(command.encode("ascii"))
        except serial.serialutil.SerialException as e:
            raise NotConnectedError from e

    def _read_reply(self, command) -> List[str]:
        """ Reads a line from the serial communication """
        reply_string = []
        for line in range(command.reply_lines):
            chunk = self._serial.readline().decode("ascii").strip()
            if chunk:
                reply_string.append(chunk)

        self.logger.debug(f"Reply received: {reply_string}")
        return reply_string

    def is_prompt_valid(self, prompt: str, command) -> bool:
        """ Verify absence of errors in prompt """

        assert 3 <= len(prompt) # unfortunately, the prompt line also holds the out of range answer, so it can be longer and information is valuable.
        if not int(prompt[0:2]) == command.target_pump_address:
            raise Elite11Exception("Pump address mismatch in reply")

        elif prompt[2:3] == "*": # address:* means stalling, address:T* means stopped at endpoint
            raise Elite11Exception("Pump is Stalling")
        elif prompt[2:3] in self.VALID_PROMPTS:
            return True

    def flush_input_buffer(self):
        """ Flushes input buffer from potentially unread messages so that write and read works as expected """
        try:
            self._serial.reset_input_buffer()
        except serial.PortNotOpenError as e:
            raise NotConnectedError from e

    def write_and_read_reply(self, command: Protocol11Command) -> List[str]:
        """  """
        with self.lock:
            self.flush_input_buffer()
            self._write(command)
            response = self._read_reply(command)
        if self.is_prompt_valid(response[-1], command):

            if "Unknown command" in response[-1]:
                raise CommandNotSupported(
                    f"The Pump command you supplied: {command} to pump {command.target_pump_address} has the following error {response}")

            elif "Out of range" in response[-1]:
                raise ArgumentNotSupported(
                    f"The Pump command you supplied: {command} to pump {command.target_pump_address} has the follwing error {response}")

            else:
                return response
        else:
            raise Elite11Exception(f"Invalid reply received from pump {command.target_pump_address}: {response}")

    @property
    def name(self) -> Optional[str]:
        try:
            return self._serial.name
        except AttributeError:
            return None


class Elite11Commands:

    """Holds the commands and arguments. Nota bene: Pump needs to be in Quick Start mode, which can be achieved from
     the display interface"""

    # collected commands
    # pump address and baud rate can be set from here, however I can't imagine a situation where this is desirable
    # Methods can be programmed onto the pump (I think via GUI) and executed via remote. this might be handy but is against the design principle of transferability
    # other not included methods: dim display, delete method, usb echo, footswitch, poll(don't really know what this does. It definately doesn't prevent manual display inputs)
    # version (verbose ver), input, output (if pin state high or low)

    # to include irun (infuse), wrun(withdraw), rrun (reverse), stp(stop), run(start), crate (current moving rate), diameter (with syr dia in mm), iramp [{start rate} {start units} {end rate} {end
    # units} {ramp time in seconds}], irate, wrate, wramp, civolume, ctvolume,cvolume, cwvolume, ivolume, svolume, tvolume, wvolume, citime, ctime,cttime,cwtime, itime, ttime, wtime, time


    # metrics command can be valuable for debugging or so, poll

    GET_VERSION = Protocol11CommandTemplate(command_string="VER", reply_lines=3)  # no args
    INFUSE = Protocol11CommandTemplate(command_string='irun', reply_lines=2)  # no args
    REVERSE_RUN = Protocol11CommandTemplate(command_string='rrun', reply_lines=2)  # no args
    RUN = Protocol11CommandTemplate(command_string='run', reply_lines=2)  # no args
    WITHDRAW = Protocol11CommandTemplate(command_string="wrun", reply_lines=2)
    STOP = Protocol11CommandTemplate(command_string='stp', reply_lines=2)  # no args

    SET_FORCE = Protocol11CommandTemplate(command_string="FORCE",
                                          reply_lines=3)  # allows parameters in range 1-100, hm modify template so it can also hold the allowed parameter range?
    ESTABLISH_CONNECTION = Protocol11CommandTemplate(command_string="\r", reply_lines=2)  # no args
    EMPTY_MESSAGE = Protocol11CommandTemplate(command_string=" ", reply_lines=2)
    METRICS = Protocol11CommandTemplate(command_string="metrics", reply_lines=22)  # no args
    CURRENT_MOVING_RATE = Protocol11CommandTemplate(command_string="crate", reply_lines=3)
    DIAMETER = Protocol11CommandTemplate(command_string="diameter",
                                         reply_lines=3)  # arg in mm, range 0.1 - 33mm
    INFUSE_RAMP = Protocol11CommandTemplate(command_string="iramp",
                                            reply_lines=3)  # returns ramp setting, if set: iramp [{start rate} {start units} {end rate} {end units} {ramp time in seconds}]
    INFUSE_RATE = Protocol11CommandTemplate(command_string="irate",
                                            reply_lines=3)  # returns or set rate irate [max | min | lim | {rate} {rate units}]
    WITHDRAW_RAMP = Protocol11CommandTemplate(command_string="wramp",
                                              reply_lines=3)  # returns ramp setting, if set: iramp [{start rate} {start units} {end rate} {end units} {ramp time in seconds}]
    WITHDRAW_RATE = Protocol11CommandTemplate(command_string="wrate",
                                              reply_lines=3)  # returns or set rate irate [max | min | lim | {rate} {rate units}]
    CLEAR_INFUSED_VOLUME = Protocol11CommandTemplate(command_string="civolume", reply_lines=2)  # no real response
    CLEAR_TARGET_VOLUME = Protocol11CommandTemplate(command_string="ctvolume", reply_lines=2)
    CLEAR_INFUSED_WITHDRAWN_VOLUME = Protocol11CommandTemplate(command_string="cvvolume", reply_lines=2)
    CLEAR_WITHDRAWN_VOLUME = Protocol11CommandTemplate(command_string="cwvolume", reply_lines=2)
    INFUSED_VOLUME = Protocol11CommandTemplate(command_string="ivolume", reply_lines=3)
    SYRINGE_VOLUME = Protocol11CommandTemplate(command_string="svolume", reply_lines=3)
    TARGET_VOLUME = Protocol11CommandTemplate(command_string="tvolume",
                                              reply_lines=3)  # tvolume [{target volume} {volume units}]
    WITHDRAWN_VOLUME = Protocol11CommandTemplate(command_string="wvolume", reply_lines=3)
    CLEAR_INFUSED_TIME = Protocol11CommandTemplate(command_string="citime", reply_lines=3)
    CLEAR_INFUSED_WITHDRAW_TIME = Protocol11CommandTemplate(command_string="ctime", reply_lines=3)
    CLEAR_TARGET_TIME = Protocol11CommandTemplate(command_string="cttime", reply_lines=3)
    CLEAR_WITHDRAW_TIME = Protocol11CommandTemplate(command_string="cwtime", reply_lines=3)
    WITHDRAWN_TIME = Protocol11CommandTemplate(command_string="wtime", reply_lines=3)
    INFUSED_TIME = Protocol11CommandTemplate(command_string="itime", reply_lines=3)
    TARGET_TIME = Protocol11CommandTemplate(command_string="ttime", reply_lines=3)  # se


class Elite11:
    """
    Not ready for full usage.  Usable with: init with syringe diameter and volume. Set target volume and rate. run.
    """

    # first pump in chain/pump connected directly to computer, if pump chain connected MUST have address 0
    def __init__(self, pump_io: PumpIO, address: int = 0, name: str = None, diameter: float = None, volume_syringe: float = None):
        """Query model and version number of firmware to check pump is
        OK. Responds with a load of stuff, but the last three characters
        are XXY, where XX is the address and Y is pump status. :, > or <
        when stopped, running forwards, or running backwards. Confirm
        that the address is correct. This acts as a check to see that
        the pump is connected and working."""

        self.name = f"Pump {self.pump_io.name}:{address}" if None else name
        self.pump_io = pump_io
        self.address = address  # This is converted to string and zfill()-ed in Protocol11Command
        self.diameter = diameter
        self.volume_syringe  = volume_syringe

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

        # This command is used to test connection: failure handled by PumpIO
        self.get_version()
        self.log.info(f"Created pump '{self.name}' w/ address '{address}' on port {self.pump_io.name}!")
        # makes sure that a 'clean' pump is initialized.
        self.clear_times()
        self.clear_volumes()
        # set the syringe-specific parameters
        if self.diameter:
            self.set_diameter(self.diameter)
        if self.volume_syringe:
            self.syringe_volume(self.volume_syringe)

        self._volume_stored = self.volume_syringe
        self._target_volume = None



    @retry(retry=retry_if_exception_type((NotConnectedError, InvalidReply)), stop=stop_after_attempt(3))
    def send_command_and_read_reply(self, command: Protocol11CommandTemplate, parameter='') -> List[str]:
        """ Sends a command based on its template and return the corresponding reply """
        # Transforms the Protocol11CommandTemplate in the corresponding Protocol11Command by adding pump address
        # if parameter is None, supply empty string
        if not parameter:
            parameter = ''
        return self.pump_io.write_and_read_reply(command.to_pump(self.address, parameter))

    @retry(retry=retry_if_exception_type(Elite11Exception), stop=stop_after_attempt(3))
    def get_version(self) -> str:
        """ Returns the current firmware version reported by the pump """
        # first, a initialisation character is sent
        self.establish_connection()
        version = self.send_command_and_read_reply(Elite11Commands.GET_VERSION)[1][3:]  # '11 ELITE I/W Single 3.0.4'

        return version

    def establish_connection(self):
        return self.send_command_and_read_reply(Elite11Commands.ESTABLISH_CONNECTION)

    def check_status(self):
        return self.send_command_and_read_reply(Elite11Commands.EMPTY_MESSAGE)

    def update_stored_volume(self):
        # not really nice, also the target_volume and rate should be class attributes?
        if self._target_volume:
            self._volume_stored -= self._target_volume

    def is_moving(self):
        status = self.check_status()
        print(status)
        if '>' in status[0] or '<' in status[0]:
            return True
        else:
            return False

#TODO when sending itime, pump will return the needed time for infusion of target volume. this could be used for time efficiency
    def run(self):
        """activates pump, runs in the previously set direction"""
        if self.is_moving():
        #should raise exception
            raise UnachievableMove("Pump already is moving")
        elif self._volume_stored < self._target_volume:
            raise UnachievableMove("Pump contains less volume than required")
        else:
            self.send_command_and_read_reply(Elite11Commands.RUN)
            # if a target volume is set, pump will only deliver thiws
            self.update_stored_volume()
        self.log.info("Pump started to run")

    def inverse_run(self):
        """activates pump, runs opposite to previously set direction"""
        self.send_command_and_read_reply(Elite11Commands.REVERSE_RUN)
        self.log.info("Pump started to run reverse")

    def infuse_run(self):
        """activates pump, runs in infuse mode"""
        self.send_command_and_read_reply(Elite11Commands.INFUSE)
        self.log.info("Pump started to infuse")

    def withdraw_run(self):
        """activates pump, runs in infuse mode"""
        self.send_command_and_read_reply(Elite11Commands.WITHDRAW)
        self.log.info("Pump started to withdraw")

    def stop(self):
        """stops pump"""
        self.send_command_and_read_reply(Elite11Commands.STOP)
        self.log.info("Pump stopped")

        #metrics, syringevolume

    def infusion_rate(self, i_rate:float = None):
        """

        :param i_rate: in mL/min, also other units can be used from syringe side. feel free to include
        :return:
        """
        if i_rate:
            i_rate = str(i_rate)+' m/m'
        self.send_command_and_read_reply(Elite11Commands.INFUSE_RATE, parameter=i_rate)

    def withdrawing_rate(self):
        self.send_command_and_read_reply(Elite11Commands.WITHDRAW_RATE)

    def infuse_ramp(self):
        self.send_command_and_read_reply(Elite11Commands.INFUSE_RAMP)

    def withdraw_ramp(self):
        self.send_command_and_read_reply(Elite11Commands.WITHDRAW_RAMP)

    def syringe_volume(self, volume: float = None):
        """

        :param volume: if supplied, sets  syringe volume. volume in mL, if µL needed: supply 0.005
        :return:
        """
        if volume:
            # from syringe side, also µL could be used or even nanoliter, with u respective n. However, imho this si simpler
            volume = str(volume) + ' m'
        return self.send_command_and_read_reply(Elite11Commands.SYRINGE_VOLUME, parameter=volume)

    def force(self, percent_force: int= None):
        """
        Allows to set or read the force.
        :param parameter: Supplied value is in % (1-100)
        :return: Force of pump
        """
        if percent_force:
            percent_force = str(percent_force)
        return self.send_command_and_read_reply(Elite11Commands.SET_FORCE, parameter=percent_force)

    def set_diameter(self, diameter: float = None):
        """
        Sets or displays the syringe diameter
        :param diameter: if supplied, sets the diameter in mm. This has to be between 1 and 33, can have 4 significant, eg 33 or 12.3456
        :return: if  no parameter supplied, returns the set diameter
        """
        return self.send_command_and_read_reply(Elite11Commands.DIAMETER, parameter=str(diameter))

    def display_current_rate(self):
        """
        If pump moves, this returns the current moving rate. Else return is not sensible
        :return: current moving rate
        """
        return self.send_command_and_read_reply(Elite11Commands.CURRENT_MOVING_RATE)

    def target_volume(self, t_volume: float = None):
        """

        :param target_volume: volume in mL 5. refer to manual
        :return:
        """
        if t_volume:
            # append unit
            self._target_volume = t_volume
            t_volume = str(t_volume) + ' m'
        return self.send_command_and_read_reply(Elite11Commands.TARGET_VOLUME, parameter=t_volume)

    def target_time(self, target_time: str):
        return self.send_command_and_read_reply(Elite11Commands.TARGET_VOLUME, parameter=target_time)

    def clear_volumes(self):
        self.send_command_and_read_reply(Elite11Commands.CLEAR_TARGET_VOLUME)
        self.send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_WITHDRAWN_VOLUME)
        self._target_volume = None

    def clear_times(self):
        self.send_command_and_read_reply(Elite11Commands.CLEAR_INFUSED_WITHDRAW_TIME)
        self.send_command_and_read_reply(Elite11Commands.CLEAR_TARGET_TIME)



# TARGET VOLuME AND TIME ARE THE THINGS TO USE!!! Rate needs to be set, infuse or withdraw, then simply start!


# TODO T* should be included, configuration script needs to be accepted (actually, since
#  this is likely to start from graph and graph should hold the relevant data, it is only important to start with that)
#  if pump in isn't in quick start mode: reply is command error Nonsystem commnds bla bla so this is caught, maybe get more explanatory logging message