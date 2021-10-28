"""
Knauer pump control.
"""
import asyncio
import logging
import warnings
from enum import Enum

from flowchem.constants import DeviceError
from flowchem.devices.Knauer.Knauer_common import KnauerEthernetDevice

FLOW = "FLOW"  # 0-50000 µL/min, int only!
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid dryrunning
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid dryrunning
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pumphead
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to highest flowrate in ml/min
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


class KnauerPumpHeads(Enum):
    """
    Two Pumpheads exist, 50 mL/min and 10 mL/min
    """

    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


class KnauerPump(KnauerEthernetDevice):
    def __init__(self, ip_address):
        super().__init__(ip_address)
        self.eol = b"\n\r"

        # All of the following are set upon initialize()
        self.max_pressure, self.max_flow = None, None
        self._headtype = None
        self._running = None

    async def initialize(self):
        """ Initialize connection """
        # Here the magic happens...
        await super().initialize()

        # Here it is checked that the device is a pump and not a valve
        await self.get_headtype()
        # Place pump in remote control
        await self.set_remote()
        # Also ensure rest state is not pumping.
        await self.stop_flow()

    @staticmethod
    def error_present(reply: str) -> bool:
        """ True if there are errors, False otherwise. Warns for errors. """

        if not reply.startswith("ERROR"):
            return False

        if "ERROR:1" in reply:
            warnings.warn(f"Invalid message sent to device.\n")

        elif "ERROR:2" in reply:
            warnings.warn(f"Setpoint refused by device.\n"
                          f"Refer to manual for allowed values.\n")
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
            self.logger.debug("setpoint successfully set!")
            return "OK"

        # Replies to 'VALUE?' are in the format 'VALUE:'
        elif message[:-1] in reply:
            self.logger.debug(f"setpoint successfully acquired, value={reply}")
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
                return await self._transmit_and_parse_reply(message + ":" + str(setpoint))

            warnings.warn(f"The setpoint provided {setpoint} is not valid for the command "
                          f"{message}!\n Accepted range is: {setpoint_range}.\n"
                          f"Command ignored")
            return ""

        # SETTER w/o range
        else:
            return await self._transmit_and_parse_reply(message + ":" + str(setpoint))

    @property
    def _headtype(self):
        """ Internal state reflecting pump one, use set_headtype() to change in pump! """
        return self.__headtype

    @_headtype.setter
    def _headtype(self, htype):
        self.__headtype = htype

        if htype == KnauerPumpHeads.FLOWRATE_TEN_ML:
            self.max_pressure, self.max_flow = 400, 10000
        elif htype == KnauerPumpHeads.FLOWRATE_FIFTY_ML:
            self.max_pressure, self.max_flow = 150, 50000

    async def get_headtype(self):
        head_type_id = await self.create_and_send_command(HEADTYPE)
        try:
            headtype = KnauerPumpHeads(int(head_type_id))
            # Sets internal property (changes max flowrate etc)
            self._headtype = headtype
        except ValueError as e:
            raise DeviceError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump.\n"
                "Only Knauer Azura Compact is supported"
            ) from e
        self.logger.debug(f"Head type of pump {self.ip_address} is {headtype}")

        return headtype

    async def set_headtype(self, head_type: KnauerPumpHeads):
        await self.create_and_send_command(HEADTYPE, setpoint=head_type.value)
        # Update internal property (changes max flowrate etc)
        self._headtype = head_type
        self.logger.debug(f"Head type set to {head_type}")

    async def get_flow(self):
        """Gets flow rate."""
        flow = await self.create_and_send_command(FLOW)
        self.logger.debug(f"Flow rate set to {flow} ml/min")
        return int(flow) / 1000

    async def set_flow(self, setpoint_in_ml_min: float = None):
        """
        Sets flow rate.

        :param setpoint_in_ml_min: in mL/min
        """
        set_flowrate_ul_min = int(setpoint_in_ml_min * 1000)
        flow = await self.create_and_send_command(
            FLOW,
            setpoint=set_flowrate_ul_min,
            setpoint_range=(0, self.max_flow + 1),
        )
        self.logger.info(f"Flow set to {setpoint_in_ml_min}, returns {flow}")

    async def get_minimum_pressure(self, pressure_in_bar=None):
        """ Gets minimum pressure. The pumps stops if the measured P is lower than this. """

        command = PMIN10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMIN50
        return await self.create_and_send_command(command)

    async def set_minimum_pressure(self, pressure_in_bar=None):
        """ Sets minimum pressure. The pumps stops if the measured P is lower than this. """

        command = PMIN10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMIN50
        await self.create_and_send_command(command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )
        logging.info(f"Minimum pressure set to {pressure_in_bar}")

    async def get_maximum_pressure(self):
        """ Gets maximum pressure. The pumps stops if the measured P is higher than this. """

        command = PMAX10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMAX50
        return await self.create_and_send_command(command)

    async def set_maximum_pressure(self, pressure_in_bar=None):
        """ Sets maximum pressure. The pumps stops if the measured P is higher than this. """

        command = PMAX10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMAX50
        await self.create_and_send_command(
            command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )
        logging.info(f"Maximum pressure set to {pressure_in_bar}")

    async def set_minimum_motor_current(self, setpoint=None):
        """ Sets minimum motor current. """
        command = IMIN10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = await self.create_and_send_command(
            command, setpoint=setpoint, setpoint_range=(0, 101)
        )
        self.logger.debug(f"Minimum motor current set to {setpoint}, returns {reply}")

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
        self.logger.debug(f"Start in required set to {value}")

    async def is_autostart_enabled(self):
        """ Returns the default behaviour of the pump upon power on. """
        reply = await self.create_and_send_command(STARTMODE)
        return bool(int(reply))

    async def enable_autostart(self, value: bool = True):
        """
        Sets the default behaviour of the pump upon power on.

        :param value: False: pause pump after switch on. True: start pumping with previous flow rate at startup
        :return: device message
        """
        await self.create_and_send_command(STARTMODE, setpoint=int(value))
        self.logger.debug(f"Autostart set to {value}")

    async def get_adjusting_factor(self):
        """ Gets the adjust parameter. Not clear what it is. """
        command = ADJ10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(command)
        return int(reply)

    async def set_adjusting_factor(self, setpoint: int = None):
        """ Sets the adjust parameter. Not clear what it is. """
        command = ADJ10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = await self.create_and_send_command(
            command, setpoint=setpoint, setpoint_range=(0, 2001)
        )
        self.logger.debug(f"Adjusting factor of set to {setpoint}, returns {reply}")

    async def get_correction_factor(self):
        """ Gets the correction factor. Not clear what it is. """
        command = CORR10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else CORR50
        return int(await self.create_and_send_command(command))

    async def set_correction_factor(self, setpoint=None):
        """ Sets the correction factor. Not clear what it is. """
        command = CORR10 if self._headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = await self.create_and_send_command(command, setpoint=setpoint, setpoint_range=(0, 301))
        self.logger.debug(f"Correction factor set to {setpoint}, returns {reply}")

    async def read_pressure(self) -> int:
        """ If the pump has a pressure sensor, returns pressure. Read-only property of course. """
        p_in_bar = await self._transmit_and_parse_reply(PRESSURE)
        self.logger.debug(f"Pressure measured = {p_in_bar} bar")
        return int(p_in_bar)

    async def read_extflow(self) -> float:
        ext_flow = await self._transmit_and_parse_reply(EXTFLOW)
        self.logger.debug(f"Extflow reading returns {ext_flow}")
        return float(ext_flow)

    async def read_errors(self):
        last_5_errors = await self.create_and_send_command(ERRORS)
        self.logger.debug(f"Error reading returns {last_5_errors}")
        return last_5_errors

    async def read_motor_current(self):
        """ Returns motor current, relative in percent 0-100. """
        current_percent = int(await self.create_and_send_command(IMOTOR))
        self.logger.debug(f"Motor current reading returns {current_percent} %")
        return current_percent

    async def start_flow(self):
        """ Starts flow """
        await self._transmit_and_parse_reply(PUMP_ON)
        self._running = True
        logging.info("Pump switched on")

    async def stop_flow(self):
        """ Stops flow """
        await self._transmit_and_parse_reply(PUMP_OFF)
        self._running = False
        logging.info("Pump switched off")

    def is_running(self):
        """ Get pump state. """
        return self._running

    async def set_local(self, state: bool = True):
        """ Relinquish remote control """
        await self.create_and_send_command(LOCAL, setpoint=int(state))
        self.logger.debug(f"Local control set to {state}")

    async def set_remote(self, state: bool = True):
        """ Set remote control on or off. """
        await self.create_and_send_command(REMOTE, setpoint=int(state))
        self.logger.debug(f"Remote control set to {state}")

    async def set_errio(self, param: bool):
        """ no idea what this exactly does... """
        await self.create_and_send_command(ERRIO, setpoint=int(param))
        self.logger.debug(f"Set errio {param}")

    async def is_analog_control_enabled(self):
        """ Returns the status of the external flow control via analog input. """
        reply = await self.create_and_send_command(EXTCONTR)
        return bool(int(reply))

    async def enable_analog_control(self, value: bool):
        """ External flow control via analog input.

        False = prevents external flow control. [0]
        True = allows the flow rate control via analog input 0 - 10V (10ml: 1 V = 1 ml/min, 50ml: 1 V = 5 ml/min). [1]
        """
        await self.create_and_send_command(EXTCONTR, setpoint=int(value))
        self.logger.debug(f"External control set to {value}")


if __name__ == '__main__':
    # This is a bug of asyncio on Windows :|
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    p = KnauerPump(ip_address="192.168.1.126")

    async def main(pump: KnauerPump):
        await pump.initialize()
        init_val = await pump.get_adjusting_factor()
        await pump.set_adjusting_factor(0)
        assert await pump.get_adjusting_factor() == 0
        await pump.set_adjusting_factor(init_val)

    asyncio.run(main(p))
