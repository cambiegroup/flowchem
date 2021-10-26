"""
Knauer valve control.
"""

import logging
from enum import Enum

from flowchem.constants import DeviceError
from flowchem.devices.Knauer.Knauer_common import KnauerEthernetDevice


class KnauerValveHeads(Enum):
    """
    Four different valve types can be used. 6port2position valve, and 6 12 16 multiposition valves
    """

    SIX_PORT_TWO_POSITION = "LI"
    SIX_PORT_SIX_POSITION = 6
    TWELVE_PORT_TWELVE_POSITION = 12
    SIXTEEN_PORT_SIXTEEN_POSITION = 16


class KnauerValve(KnauerEthernetDevice):
    """
    Class to control Knauer multi position valves.

    Valve type can be 6, 12, 16
    or it can be 6 ports, two positions, which will be simply 2 (two states)
    in this case,response for T is LI. load and inject can be switched by sending log or i
    maybe valves should have an initial state which is set during init and updated, if no  change don't schedule command
    https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_benutzerhandbuch_de.pdf
    dip switch for valve selection
    """

    def __init__(self, ip_address, port=KnauerEthernetDevice.TCP_PORT, buffersize=KnauerEthernetDevice.BUFFER_SIZE):

        super().__init__(ip_address, port, buffersize)

        self._valve_state = self.get_current_position()
        # this gets the valve type as valve [type] and strips away valve_
        self.valve_type = self.get_valve_type()  # checks against allowed valve types

    def communicate(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = super()._send_and_receive_handler(str(message) + "\r\n")
        if reply == "?":
            # retry once
            reply = super()._send_and_receive_handler(str(message) + "\r\n")
            if reply == "?":
                DeviceError(
                    f"Command not supported, your valve is of type {self.valve_type}"
                )
        try:
            reply = int(reply)
        except ValueError:
            pass
        return reply

    def get_current_position(self):
        curr_pos = self.communicate("P")
        logging.debug(f"Current position is {curr_pos}")

        return curr_pos

    def switch_to_position(self, position: int or str):
        try:
            position = int(position)
        except ValueError:
            pass

        # allows lower and uppercase commands in case of injection
        if isinstance(position, str):
            position = position.upper()

        # switching necessary?
        if position == self._valve_state:
            logging.debug("already at that position")
            return

        # change to selected position
        reply = self.communicate(position)

        # check if this was done
        if reply == "OK":
            logging.debug("switching successful")
            self._valve_state = position

        elif "E0" in reply:

            logging.error("valve was not switched because valve refused")
            raise DeviceError("valve was not switched because valve refused")

        elif "E1" in reply:
            logging.error("Motor current to high. Check that")
            raise DeviceError("Motor current to high. Check that")

        else:
            raise DeviceError(f"Unknown reply received. Reply is {reply}")

    def get_valve_type(self):
        """aquires valve type, if not supported will throw error.
        This also prevents to initialize some device as a KnauerValve"""
        reply = self.communicate("T")[6:]
        # could be more pretty by passing expected answer to communicate
        try:
            reply = int(reply)
        except ValueError:
            pass
        try:
            headtype = KnauerValveHeads(reply)
        except ValueError as e:
            raise DeviceError(
                f"It seems you're trying instantiate a unknown device/unknown valve type {e} as Knauer Valve."
                "Only Valves of type 16, 12, 10 and LI are supported"
            ) from e
        logging.info(
            f"Valve successfully connected, Type is {headtype} at address {self.ip_address}"
        )
        return headtype

    def close_connection(self):
        logging.info(f"Valve at address closed connection {self.ip_address}")
        self.sock.close()


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
IMOTOR = "IMOTOR?"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS?"  # displays last 5 error codes
EXTCONTR = (
    "EXTCONTR:"  # 0, 1; 1= allows flow control via external analog input, 0 dont allow
)
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow