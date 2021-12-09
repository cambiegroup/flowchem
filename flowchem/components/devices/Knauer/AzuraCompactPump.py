"""
Knauer pump control.
"""
import asyncio
import warnings
from typing import List

from loguru import logger
from enum import Enum

from flowchem.components.devices.Knauer.Knauer_common import KnauerEthernetDevice
from flowchem.components.stdlib import Pump
from flowchem.exceptions import DeviceError
from flowchem.units import flowchem_ureg

FLOW = "FLOW"  # 0-50000 µL/min, int only!
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to highest flowrate in ml/min
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid dryrunning
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid dryrunning
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pumphead
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
STARTLEVEL = "STARTLEVEL"  # 0, 1 configures start. 0 -> only start pump when shorted to GND, 1 -> always allow start
ERRIO = "ERRIO"  # 0, 1 write/read error in/output ??? sets errio either 1 or 0, reports errio:ok
STARTMODE = "STARTMODE"  # 0, 1; 0=pause pump after switchon, 1=start immediatley with previous set flow rate
ADJ10 = "ADJ10"  # 100-2000
ADJ50 = "ADJ50"  # 100-2000
CORR10 = "CORR10"  # 0-300
CORR50 = "CORR50"  # 0-300
EXTFLOW = "EXTFLOW?"
IMOTOR = "IMOTOR"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS"  # displays last 5 error codes
EXTCONTR = "EXTCONTR"  # allows flow control via analog input
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow


class AzuraPumpHeads(Enum):
    """Two Pump heads are available for the Azura: 50 mL/min and 10 mL/min."""

    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


class AzuraCompactPump(KnauerEthernetDevice, Pump):
    """Control module for Knauer Azura Compact pumps."""

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

    def __init__(
        self, ip_address=None, mac_address=None, name=None, max_pressure: str = None
    ):
        super().__init__(ip_address, mac_address, name)
        self.eol = b"\n\r"

        # All of the following are set upon initialize()
        self.max_allowed_pressure, self.max_allowed_flow = 0, 0
        self._headtype = None
        self._running = None
        self._pressure_limit = max_pressure

        self.rate = flowchem_ureg.parse_expression("0 ml/min")
        self._base_state = dict(rate="0 mL/min")

    async def initialize(self):
        """Initialize connection"""
        # Here the magic happens...
        await super().initialize()

        # Here it is checked that the device is a pump and not a valve
        await self.get_headtype()
        # Place pump in remote control
        await self.set_remote()
        # Also ensure rest state is not pumping.
        await self.stop_flow()

        if self._pressure_limit is not None:
            await self.set_maximum_pressure(self._pressure_limit)

    @staticmethod
    def error_present(reply: str) -> bool:
        """True if there are errors, False otherwise. Warns for errors."""

        # ERRORS: is the expected answer to read_errors()
        if not reply.startswith("ERROR") or reply.startswith("ERRORS:"):
            return False

        if "ERROR:1" in reply:
            warnings.warn("Invalid message sent to device.\n")

        elif "ERROR:2" in reply:
            warnings.warn(
                "Setpoint refused by device.\n" "Refer to manual for allowed values.\n"
            )
        else:
            warnings.warn("Unspecified error detected!")
        return True

    async def _transmit_and_parse_reply(self, message: str) -> str:
        """
        sends command and receives reply, deals with all communication based stuff and checks
        that the valve is of expected type
        :param message:
        :return: reply: str
        """
        reply = await self._send_and_receive(message)
        if self.error_present(reply):
            return ""

        # Setpoint ok
        elif ":OK" in reply:
            logger.debug("setpoint successfully set!")
            return "OK"

        # Replies to 'VALUE?' are in the format 'VALUE:'
        elif message[:-1] in reply:
            logger.debug(f"setpoint successfully acquired, value={reply}")
            # Last value after colon
            return reply.split(":")[-1]

        # No reply
        elif not reply:
            warnings.warn("No reply received")
            return ""

        warnings.warn(f"Unrecognized reply: {reply}")
        return reply

    async def create_and_send_command(
        self, message, setpoint: int = None, setpoint_range: tuple = None
    ):
        """
        Create and sends a message from the command.

        If setpoint is given, then the command is appended with :value
        If not setpoint is given, a "?" is added for getter syntax

        e.g. message = "HEADTYPE"
        no setpoint -> sends "HEADTYPE?"
        w/ setpoint -> sends "HEADTYPE:<setpoint_value>"
        """
        # GETTER
        if setpoint is None:
            return await self._transmit_and_parse_reply(message + "?")

        # SETTER with range
        if setpoint_range:
            if setpoint in range(*setpoint_range):
                return await self._transmit_and_parse_reply(
                    message + ":" + str(setpoint)
                )

            warnings.warn(
                f"The setpoint provided {setpoint} is not valid for the command "
                f"{message}!\n Accepted range is: {setpoint_range}.\n"
                f"Command ignored"
            )
            return ""

        # SETTER w/o range
        else:
            return await self._transmit_and_parse_reply(message + ":" + str(setpoint))

    @property
    def _headtype(self):
        """Internal state reflecting pump one, use set_headtype() to change in pump!"""
        return self.__headtype

    @_headtype.setter
    def _headtype(self, htype):
        self.__headtype = htype

        if htype == AzuraPumpHeads.FLOWRATE_TEN_ML:
            self.max_allowed_pressure, self.max_allowed_flow = 400, 10000
        elif htype == AzuraPumpHeads.FLOWRATE_FIFTY_ML:
            self.max_allowed_pressure, self.max_allowed_flow = 150, 50000

    async def get_headtype(self) -> AzuraPumpHeads:
        """Returns pump's head type."""
        head_type_id = await self.create_and_send_command(HEADTYPE)
        try:
            headtype = AzuraPumpHeads(int(head_type_id))
            # Sets internal property (changes max flowrate etc)
            self._headtype = headtype
        except ValueError as e:
            raise DeviceError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump.\n"
                "Only Knauer Azura Compact is supported"
            ) from e
        logger.debug(f"Head type of pump {self.ip_address} is {headtype}")

        return headtype

    async def set_headtype(self, head_type: AzuraPumpHeads):
        """Sets pump's head type."""
        await self.create_and_send_command(HEADTYPE, setpoint=head_type.value)
        # Update internal property (changes max flowrate etc)
        self._headtype = head_type
        logger.debug(f"Head type set to {head_type}")

    async def get_flow(self) -> str:
        """ Gets flow rate. """
        flow_value = await self.create_and_send_command(FLOW)
        flowrate = flowchem_ureg(f"{flow_value} ul/min")
        logger.debug(f"Current flow rate is {flowrate}")
        return str(flowrate.to("ml/min"))

    async def set_flow(self, flowrate: str = None):
        """ Sets flow rate.

        :param flowrate: string with units
        """
        parsed_flowrate = flowchem_ureg(flowrate)
        await self.create_and_send_command(
            FLOW,
            setpoint=round(parsed_flowrate.m_as("ul/min")),
            setpoint_range=(0, self.max_allowed_flow + 1),
        )
        logger.info(f"Flow set to {flowrate}")

    async def get_minimum_pressure(self):
        """Gets minimum pressure. The pumps stops if the measured P is lower than this."""

        command = PMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMIN50
        p_min = await self.create_and_send_command(command) * flowchem_ureg.bar
        return str(p_min)

    async def set_minimum_pressure(self, value: str = "0 bar"):
        """ Sets minimum pressure. The pumps stops if the measured P is lower than this. """

        pressure = flowchem_ureg(value)
        command = PMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMIN50
        await self.create_and_send_command(
            command,
            setpoint=round(pressure.m_as("bar")),
            setpoint_range=(0, self.max_allowed_pressure + 1),
        )
        logger.info(f"Minimum pressure set to {pressure}")

    async def get_maximum_pressure(self) -> str:
        """Gets maximum pressure. The pumps stops if the measured P is higher than this."""

        command = PMAX10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMAX50
        p_max = await self.create_and_send_command(command) * flowchem_ureg.bar
        return str(p_max)

    async def set_maximum_pressure(self, value: str):
        """ Sets maximum pressure. The pumps stops if the measured P is higher than this. """

        pressure = flowchem_ureg(value)
        command = PMAX10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else PMAX50
        await self.create_and_send_command(
            command,
            setpoint=round(pressure.m_as("bar")),
            setpoint_range=(0, self.max_allowed_pressure + 1),
        )
        logger.info(f"Maximum pressure set to {pressure}")

    async def set_minimum_motor_current(self, setpoint=None):
        """Sets minimum motor current."""
        command = IMIN10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = await self.create_and_send_command(
            command, setpoint=setpoint, setpoint_range=(0, 101)
        )
        logger.debug(f"Minimum motor current set to {setpoint}, returns {reply}")

    async def is_start_in_required(self):
        """
        Check state of START IN. See require_start_in() for details.
        """
        runlevel = await self.create_and_send_command(STARTLEVEL)
        return not bool(int(runlevel))

    async def require_start_in(self, value: bool = True):
        """
        Configures START IN. If required, the pump starts only if the STARTIN pin is shortened to GND.

        True = Pump starts the flow at short circuit contact only. (Start In <> Ground). [0]
        False = Pump starts the flow without a short circuit contact. (Start In <> Ground). [1]
        """
        setpoint = int(not value)
        await self.create_and_send_command(STARTLEVEL, setpoint=setpoint)
        logger.debug(f"Start in required set to {value}")

    async def is_autostart_enabled(self):
        """Returns the default behaviour of the pump upon power on."""
        reply = await self.create_and_send_command(STARTMODE)
        return bool(int(reply))

    async def enable_autostart(self, value: bool = True):
        """
        Sets the default behaviour of the pump upon power on.

        :param value: False: pause pump after switch on. True: start pumping with previous flow rate at startup
        :return: device message
        """
        await self.create_and_send_command(STARTMODE, setpoint=int(value))
        logger.debug(f"Autostart set to {value}")

    async def get_adjusting_factor(self):
        """Gets the adjust parameter. Not clear what it is."""
        command = ADJ10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(command)
        return int(reply)

    async def set_adjusting_factor(self, setpoint: int = None):
        """Sets the adjust parameter. Not clear what it is."""
        command = ADJ10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(
            command, setpoint=setpoint, setpoint_range=(0, 2001)
        )
        logger.debug(f"Adjusting factor of set to {setpoint}, returns {reply}")

    async def get_correction_factor(self):
        """Gets the correction factor. Not clear what it is."""
        command = CORR10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else CORR50
        return int(await self.create_and_send_command(command))

    async def set_correction_factor(self, setpoint=None):
        """Sets the correction factor. Not clear what it is."""
        command = CORR10 if self._headtype == AzuraPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = await self.create_and_send_command(
            command, setpoint=setpoint, setpoint_range=(0, 301)
        )
        logger.debug(f"Correction factor set to {setpoint}, returns {reply}")

    async def read_pressure(self) -> str:
        """ If the pump has a pressure sensor, returns pressure. Read-only property of course. """
        pressure = await self._transmit_and_parse_reply(PRESSURE) * flowchem_ureg.bar
        logger.debug(f"Pressure measured = {pressure}")
        return str(pressure)

    async def read_extflow(self) -> float:
        """Read the set flowrate from analog in."""
        ext_flow = await self._transmit_and_parse_reply(EXTFLOW)
        logger.debug(f"Extflow reading returns {ext_flow}")
        return float(ext_flow)

    async def read_errors(self) -> List[int]:
        """Returns the last 5 errors."""
        last_5_errors = await self.create_and_send_command(ERRORS)
        logger.debug(f"Error reading returns {last_5_errors}")
        parsed_errors = [int(err_code) for err_code in last_5_errors.split(",")]
        return parsed_errors

    async def read_motor_current(self):
        """Returns motor current, relative in percent 0-100."""
        current_percent = int(await self.create_and_send_command(IMOTOR))
        logger.debug(f"Motor current reading returns {current_percent} %")
        return current_percent

    async def start_flow(self):
        """Starts flow"""
        await self._transmit_and_parse_reply(PUMP_ON)
        self._running = True
        logger.info("Pump switched on")

    async def stop_flow(self):
        """Stops flow"""
        await self._transmit_and_parse_reply(PUMP_OFF)
        self._running = False
        logger.info("Pump not pumping")

    def is_running(self):
        """Get pump state."""
        return self._running

    async def set_local(self, state: bool = True):
        """Relinquish remote control"""
        await self.create_and_send_command(LOCAL, setpoint=int(state))
        logger.debug(f"Local control set to {state}")

    async def set_remote(self, state: bool = True):
        """Set remote control on or off."""
        await self.create_and_send_command(REMOTE, setpoint=int(state))
        logger.debug(f"Remote control set to {state}")

    async def set_errio(self, param: bool):
        """no idea what this exactly does..."""
        await self.create_and_send_command(ERRIO, setpoint=int(param))
        logger.debug(f"Set errio {param}")

    async def is_analog_control_enabled(self):
        """Returns the status of the external flow control via analog input."""
        reply = await self.create_and_send_command(EXTCONTR)
        return bool(int(reply))

    async def enable_analog_control(self, value: bool):
        """External flow control via analog input.

        False = prevents external flow control. [0]
        True = allows the flow rate control via analog input 0 - 10V (10ml: 1 V = 1 ml/min, 50ml: 1 V = 5 ml/min). [1]
        """
        await self.create_and_send_command(EXTCONTR, setpoint=int(value))
        logger.debug(f"External control set to {value}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop_flow()

    async def _update(self):
        """Called automatically to change flow rate."""

        if self.rate == 0:
            await self.stop_flow()
        else:
            await self.set_flow(self.rate)
            await self.start_flow()

    def get_router(self):
        """Creates an APIRouter for this object."""
        from fastapi import APIRouter

        router = APIRouter()
        router.add_api_route("/flow", self.get_flow, methods=["GET"])
        router.add_api_route("/flow", self.set_flow, methods=["PUT"])
        router.add_api_route("/pressure", self.read_pressure, methods=["GET"])
        router.add_api_route("/start", self.start_flow, methods=["PUT"])
        router.add_api_route("/stop", self.stop_flow, methods=["PUT"])
        return router


if __name__ == "__main__":
    # This is a bug of asyncio on Windows :|
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    p = AzuraCompactPump(ip_address="192.168.10.113")

    async def main(pump: AzuraCompactPump):
        """Test function"""
        await pump.initialize()
        await pump.set_flow("0.1 ml/min")
        await pump.start_flow()
        await asyncio.sleep(5)
        await pump.stop_flow()

    asyncio.run(main(p))
