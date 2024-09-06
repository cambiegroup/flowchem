import sys
#sys.path.append('W:\\BS-Automated\\Miguel\\github\\flowchem\\flowchem_fork\\src')
import socket
from enum import Enum, auto
from loguru import logger
import logging
from time import sleep
from typing import Type, List
import functools

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import jakob, Samuel_Saraiva, miguel
from flowchem.devices.knauer._common import KnauerEthernetDevice
from flowchem.devices.knauer.knauer_autosampler_component import (
    AutosamplerCNC,
    AutosamplerPump,
    AutosamplerSyringeValve,
    AutosamplerInjectionValve,
)

try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False


class ASError(Exception):
    pass


class CommunicationError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class CommandOrValueError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class ASBusyError(ASError):
    """AS is currently busy but will accept your command at another point of time"""
    pass


class CommandModus(Enum):
    SET = auto()
    GET_PROGRAMMED = auto()
    GET_ACTUAL = auto()


# wrapper that executes for a maximum amount of time until positive reply received
def send_until_acknowledged(func, max_reaction_time=10, time_between=0.01):
    @functools.wraps(func)
    def wrapper(*args, max_reaction_time=max_reaction_time, time_between=time_between, **kwargs, ):
        while True:
            try:
                return func(*args, **kwargs)
            except ASBusyError:
                # AS is rather fast so this sounds like a reasonable time
                sleep(time_between)
                max_reaction_time -= time_between
                if max_reaction_time <= 0:
                    raise ASError

    return wrapper


class ASEthernetDevice:
    TCP_PORT = 2101
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, buffersize=None, tcp_port=None):
        self.ip_address = str(ip_address)
        self.port = tcp_port if tcp_port else ASEthernetDevice.TCP_PORT
        self.buffersize = buffersize if buffersize else ASEthernetDevice.BUFFER_SIZE

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    def _send_and_receive(self, message: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip_address, self.port))

                s.send(message.encode())
                reply = b""
                while True:
                    chunk = s.recv(ASEthernetDevice.BUFFER_SIZE)
                    reply += chunk
                    try:
                        CommunicationFlags(chunk)
                        break
                    except ValueError:
                        pass
                    if CommunicationFlags.MESSAGE_END.value in chunk:
                        break
            return reply
        except socket.timeout:
            logging.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with ip_address {self.ip_address}"
            )


class KnauerAutosampler(ASEthernetDevice, FlowchemDevice):
    """Autosampler control class."""

    def __init__(self,
                 ip_address=None,
                 mac_address=None,
                 autosampler_id: int = 0,
                 tray_type: str = "TRAY_48_VIAL",
                 **kwargs,
                 ):
        super().__init__(ip_address, mac_address, **kwargs)
        self.autosampler_id = autosampler_id
        self.tray_type = tray_type
        self.device_info = DeviceInfo(
            authors=[jakob, miguel, Samuel_Saraiva],
            maintainers=[jakob, miguel, Samuel_Saraiva],
            manufacturer="Knauer",
            model="Autosampler AS 6.1L"
        )

    def _construct_communication_string(self, command: Type[CommandStructure], modus: str,
                                        *args: int or str, **kwargs: str) -> str:
        # input can be strings, is translated to enum internally -> enum no need to expsoe
        # if value cant be translated to enum, just through error with the available options
        command_class = command()
        modus = modus.upper()

        if modus == CommandModus.SET.name:
            command_class.set_values(*args, **kwargs)
            communication_string = command_class.return_setting_string()

        elif modus == CommandModus.GET_PROGRAMMED.name:
            communication_string = command_class.query_programmed()

        elif modus == CommandModus.GET_ACTUAL.name:
            communication_string = command_class.query_actual()

        else:
            raise CommandOrValueError(f"You set {modus} as command modus, however modus should be {CommandModus.SET.name},"
                                      f" {CommandModus.GET_ACTUAL.name}, {CommandModus.GET_PROGRAMMED.name} ")
        return f"{CommunicationFlags.MESSAGE_START.value.decode()}{self.autosampler_id}" \
               f"{ADDITIONAL_INFO}{communication_string}" \
               f"{CommunicationFlags.MESSAGE_END.value.decode()}"

    @send_until_acknowledged
    def _set(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)
        # this only checks that it was acknowledged
        self._parse_setting_reply(reply)

    @send_until_acknowledged
    def _query(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)

        query_reply = self._parse_query_reply(reply)
        return query_reply

    def _parse_setting_reply(self, reply):
        # reply needs to be binary string

        if reply == CommunicationFlags.ACKNOWLEDGE.value:
            return True
        elif reply == CommunicationFlags.TRY_AGAIN.value:
            raise ASBusyError
        elif reply == CommunicationFlags.NOT_ACKNOWLEDGE.value:
            raise CommandOrValueError
        # this is only the case with replies on queries
        else:
            raise ASError(f"The reply is {reply} and does not fit the expected reply for value setting")

    def _parse_query_reply(self, reply)->int:
        reply_start_char, reply_stripped, reply_end_char = reply[:ReplyStructure.STX_END.value], \
                                                           reply[
                                                           ReplyStructure.STX_END.value:ReplyStructure.ETX_START.value], \
                                                           reply[ReplyStructure.ETX_START.value:]
        if reply_start_char != CommunicationFlags.MESSAGE_START.value or reply_end_char != CommunicationFlags.MESSAGE_END.value:
            raise CommunicationError


        # basically, if the device gives an extended reply, length will be 14. This only matters for get commands
        if len(reply_stripped) == 14:
        # decompose further
            as_id = reply[ReplyStructure.STX_END.value:ReplyStructure.ID_END.value]
            as_ai = reply[ReplyStructure.ID_END.value:ReplyStructure.AI_END.value]
            as_pfc = reply[ReplyStructure.AI_END.value:ReplyStructure.PFC_END.value]
            as_val = reply[ReplyStructure.PFC_END.value:ReplyStructure.VALUE_END.value]
            # check if reply from requested device
            if int(as_id.decode()) != self.autosampler_id:
                raise ASError(f"ID of used AS is {self.autosampler_id}, but ID in reply is as_id")
            # if reply is only zeros, which can be, give back one 0 for interpretion
            if len(as_val.decode().lstrip("0")) > 0:
                return int(as_val.decode().lstrip("0"))
            else:
                return int(as_val.decode()[-1:])
            # check the device ID against current device id
        else:
            raise ASError(f"AS reply did not fit any of the known patterns, reply is: {reply_stripped}")

    def _set_get_value(self, command:Type[CommandStructure], parameter:int or None=None, reply_mapping: None or Type[Enum] = None, get_actual = False):
        """If get actual is set true, the actual value is queried, otherwise the programmed value is queried (default)"""
        if parameter:
            command_string = self._construct_communication_string(command, CommandModus.SET.name, parameter)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(command, CommandModus.GET_PROGRAMMED.name if not get_actual else CommandModus.GET_ACTUAL.name)
            reply = self._query(command_string)
            if reply_mapping:
                return reply_mapping(reply).name
            else:
                return reply

    async def initialize(self):
        """Initialize."""
        # Sets initial positions of needle and valve
        self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        self.syringe_valve_position(SyringeValvePositions.WASTE.name)
        self.injector_valve_position(InjectorValvePositions.LOAD.name)

        logger.info('KnauerAutosampler device was successfully initialized!')
        self.components.extend([
            AutosamplerCNC("cnc", self, self.tray_layout),
            AutosamplerPump("pump", self),
            AutosamplerSyringeValve("syringe_valve", self),
            AutosamplerInjectionValve("injection_valve", self),
        ])


    def _move_needle_horizontal(self, needle_position:str, plate: str = None, well: int = None):
        command_string = self._construct_communication_string(NeedleHorizontalCommand, CommandModus.SET.name, needle_position, plate, well)
        return self._set(command_string)

    def _move_needle_vertical(self, move_to: str):
        command_string = self._construct_communication_string(MoveNeedleVerticalCommand, CommandModus.SET.name, move_to)
        return self._set(command_string)

    def syringe_valve_position(self, port: str = None):
        # TODO check if this mapping offset can be fixed elegantly
        if port:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.SET.name, port)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.GET_ACTUAL.name)
            raw_reply = self._query(command_string) - 1
            return SwitchSyringeValveCommand.syringe_valve_positions(raw_reply).name

    def injector_valve_position(self, port: str = None):
        return self._set_get_value(SwitchInjectorValveCommand, port, SwitchInjectorValveCommand.allowed_position, get_actual=True)

    def aspirate(self, volume: float, flow_rate: float or int = None):
        """
        aspirate with buildt in syringe if no external syringe is set to autosampler.
        Else use extrernal syringe
        Args:
            volume: volume to aspirate in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)
        return self._set(command_string)


    def dispense(self, volume, flow_rate=None):
        """
        dispense with buildt in syringe if no external syringe is set to autosampler.
        Else use external syringe
        Args:
            volume: volume to dispense in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if flow_rate is not None:
            raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
        volume = int(round(volume, 3) * 1000)
        command_string = self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)
        return self._set(command_string)

    def _move_tray(self, tray_type: str, sample_position: str or int):
        command_string = self._construct_communication_string(MoveTrayCommand, CommandModus.SET.name,
                                                              tray_type, sample_position)
        return self._set(command_string)



if __name__ == "__main__":
    trays = {
        0: (8, 6),  # Tray 0 with 6 rows and 8 columns
        1: (8, 6)  # Tray 1 with 6 rows and 8 columns
    }

    AS = KnauerAutosampler(
        name="test-AS",
        ip_address=None,
        mac_address=None,
        autosampler_id=0,
        tray_layout=trays,
    )

    command = AS._construct_communication_string(DispenseCommand, CommandModus.SET.name, 1)