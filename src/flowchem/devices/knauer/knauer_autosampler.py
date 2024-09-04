import sys

sys.path.append('W:\\BS-Automated\\Miguel\\github\\flowchem\\flowchem_fork\\src')

import socket
from enum import Enum, auto
from loguru import logger
import logging
from time import sleep

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


class KnauerAutosampler(KnauerEthernetDevice, FlowchemDevice):
    """Autosampler control class."""

    def __init__(self,
                 ip_address=None,
                 mac_address=None,
                 autosampler_id: int = 0,
                 **kwargs,
                 ):
        super().__init__(ip_address, mac_address, **kwargs)
        self.device_info = DeviceInfo(
            authors=[jakob, miguel, Samuel_Saraiva],
            maintainers=[jakob, miguel, Samuel_Saraiva],
            manufacturer="Knauer",
            model="Autosampler AS 6.1L",
            autosampler_id=autosampler_id
        )

    async def initialize(self):
        """Initialize connection."""
        await super().initialize()

        # Sets initial positions of needle and valve
        self._move_needle_vertical(NeedleVerticalPositions.UP.name)
        self._move_needle_horizontal(NeedleHorizontalPosition.WASTE.name)
        self.syringe_valve_position(SyringeValvePositions.WASTE.name)
        self.injector_valve_position(InjectorValvePositions.LOAD.name)

        logger.info('KnauerAutosampler device was successfully initialized!')
        self.components.extend([
            AutosamplerCNC("cnc", self),
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

    def syringe_valve_position(self, port:str = None):
        # TODO check if this mapping offset can be fixed elegantly
        if port:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.SET.name, port)
            return self._set(command_string)
        else:
            command_string = self._construct_communication_string(SwitchSyringeValveCommand, CommandModus.GET_ACTUAL.name)
            raw_reply = self._query(command_string) - 1
            return SwitchSyringeValveCommand.syringe_valve_positions(raw_reply).name

    def injector_valve_position(self, port:str = None):
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
        if not self.external_syringe_aspirate:
            if flow_rate is not None:
                raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
            volume = int(round(volume, 3) * 1000)
            command_string = self._construct_communication_string(AspirateCommand, CommandModus.SET.name, volume)
            return self._set(command_string)
        else:
            assert self.external_syringe_dispense is not None and self.external_syringe_ready is not None, "Make sure to set all necessary commands for external syringe"
            self.external_syringe_aspirate(volume, flow_rate)

    def dispense(self, volume, flow_rate=None):
        """
        dispense with buildt in syringe if no external syringe is set to autosampler.
        Else use external syringe
        Args:
            volume: volume to dispense in mL
            flow_rate: flowrate in mL/min. Only works on external syringe. If buildt-in syringe is used, use default value

        Returns: None

        """
        if not self.external_syringe_dispense:
            if flow_rate is not None:
                raise NotImplementedError("Buildt in syringe does not allow to control flowrate")
            volume = int(round(volume, 3) * 1000)
            command_string = self._construct_communication_string(DispenseCommand, CommandModus.SET.name, volume)
            return self._set(command_string)
        else:
            assert self.external_syringe_aspirate is not None and self.external_syringe_ready is not None, "Make sure to set all necessary commands for external syringe"
            self.external_syringe_dispense(volume, flow_rate)

if __name__ == "__main__":
    AS = KnauerAutosampler.from_config(
        ip_address="",
        AS_id=61,
        tcp_port=2101,
        buffer_size=1024,
    )
