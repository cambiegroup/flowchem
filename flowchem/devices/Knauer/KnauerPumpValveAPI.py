"""
Module for communication with Knauer pumps and valves.
"""

# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer


import logging
import socket
import time
from enum import Enum


class KnauerError(Exception):
    pass


class SwitchingException(KnauerError):
    pass


class ParameterError(KnauerError):
    pass


class CommandError(KnauerError):
    pass



class KnauerPumpHeads(Enum):
    """
    Two Pumpheads exist, 50 mL/min and 10 mL/min
    """
    FLOWRATE_FIFTY_ML = 50
    FLOWRATE_TEN_ML = 10


class KnauerValveHeads(Enum):
    """
    Four different valve types can be used. 6port2position valve, and 6 12 16 multiposition valves
    """
    SIX_PORT_TWO_POSITION = 'LI'
    SIX_PORT_SIX_POSITION = 6
    TWELVE_PORT_TWELVE_POSITION = 12
    SIXTEEN_PORT_SIXTEEN_POSITION = 16




""" CONSTANTS """
class KnauerCommunicationConstants(Enum):

    TCP_PORT = 10001
    BUFFER_SIZE = 1024


class EthernetDevice:
    def __init__(self, address, port, buffersize):
        self.address = str(address)
        self.port = int(port)
        self.buffersize = buffersize
        self.sock = self._try_connection()
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

    def __del__(self):
        self.sock.close()

    def _try_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set timeout to 5s
        sock.settimeout(5)
        try:
            sock.connect((self.address, self.port))
        except socket.timeout:
            logging.error('No connection possible to device with IP {}'.format(self.address))
            raise ConnectionError('No Connection possible to device with address {}'.format(self.address))
        return sock

    def _send_and_receive(self, message):
        self.sock.send(message.encode())
        time.sleep(0.01)
        reply = ''
        while True:
            chunk = self.sock.recv(self.buffersize).decode()
            reply += chunk
            if "\r" in chunk:
                break
        return reply.strip('\r')

    # idea is: try to send message, when reply is received return that. returned reply can be checked against expected
    def _send_and_receive_handler(self, message):
        try:
            reply=self._send_and_receive(message)
        # use other error. if socket somehow ceased to exist, try to reestablish connection. if not possible, rause error
        except socket.timeout:
            try:
            # logger: tell response received, might be good to resend
                # try to reestablish connection, send and receive afterwards
                self.sock = self._try_connection(self.address, self.port)
                reply = self._send_and_receive(message)
            # no further handling necessery, if this does not work there is a serious problem. Powercycle or check hardware
            except OSError:
                raise ConnectionError('Failed to reestablish connection to {}'.format(self.address))
        return reply


class KnauerValve(EthernetDevice):
    """
    Class to control Knauer multi position valves.

    Valve type can be 6, 12, 16
    or it can be 6 ports, two positions, which will be simply 2 (two states)
    in this case,response for T is LI. load and inject can be switched by sending l or i
    maybe valves should have an initial state which is set during init and updated, if no  change don't schedule command
    https://www.knauer.net/Dokumente/valves/azura/manuals/v6860_azura_v_2.1s_benutzerhandbuch_de.pdf
    dip switch for valve selection
    """
    def __init__(self, address, port=KnauerCommunicationConstants.TCP_PORT.value,
                 buffersize=KnauerCommunicationConstants.BUFFER_SIZE.value):

        super().__init__(address, port, buffersize)

        self._valve_state = self.get_current_position()
        # this gets the valve type as valve [type] and strips away valve_
        self.valve_type= self.get_valve_type() # checks against allowed valve types



    def communicate(self, message: str or int):
        """
        sends command and receives reply, deals with all communication based stuff and checks that the valve is of expected type
        :param message:
        :return: reply: str
        """
        reply = super()._send_and_receive_handler(str(message)+'\r\n')
        if reply == "?":
            # retry once
            reply = super()._send_and_receive_handler(str(message) + '\r\n')
            if reply == "?":
                CommandError('Command not supported, your valve is of type'+ self.valve_type)
        try:
            reply=int(reply)
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
            logging.debug('already at that position')

        else:
            #these prechecks are not really necessery, since sending wrong value would throw an error by wrong reply
            # check if switching can be achieved
            if self.valve_type == KnauerValveHeads.SIX_PORT_TWO_POSITION:
                if position not in self.valve_type.value:
                    SwitchingException('Internal check: Position {} not available on instantiated valve {}'.format(position, self.valve_type))

            if self.valve_type != KnauerValveHeads.SIX_PORT_TWO_POSITION:
                try:
                    if not 0 <= position <= self.valve_type.value:
                        SwitchingException('Internal Check: Position {} not available on instantiated valve {}'.format(position, self.valve_type))
                except TypeError:
                    raise ParameterError(f'Please provide a number to switch to. You provided {position}')

        # change to selected position
            reply = self.communicate(position)
            # check if this was done
            if reply == "OK":
                logging.debug('switching successful')
                self._valve_state = position


            elif reply == "E0":
                logging.error('valve was not switched because valve refused')
                raise SwitchingException('valve was not switched because valve refused')

            elif reply == "E1":
                logging.error('Motor current to high. Check that')
                raise SwitchingException('Motor current to high. Check that')

            else:
                raise SwitchingException('Unknown reply received. Reply is ' + reply)

    def get_valve_type(self):
        """aquires valve type, if not supported will throw error. This also prevents to initialize some device as a KnauerValve"""
        reply = self.communicate('T')[6:]
        # could be more pretty by passing expected answer to communicate
        try:
            reply=int(reply)
        except ValueError:
            pass
        try:
            headtype= KnauerValveHeads(reply)
        except ValueError as e:
            raise KnauerError(f'It seems you\'re trying instantiate a unknown device/unknown valve type {e} as Knauer Valve.'
                  'Only Valves of type 16, 12, 10 and LI are supported') from e
        logging.info(f'Valve successfully connected, Type is {headtype} at address {self.address}')
        return headtype

    def close_connection(self):
        logging.info('Valve at address closed connection {}'.format(self.address))
        self.sock.close()


# Read and write, read: command?; write = command:setpoint
# BEWARE MANUAL STATES 0-50000µml/min HOWEVER this depends on headtype
FLOW = "FLOW"  # 0-50000 µL/min, int only!
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid dryrunning
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid dryrunning
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pumphead
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to highest flowrate in ml/min
STARTLEVEL = "STARTLEVEL"  # 0, 1 configures start in: 0 means only start pump when shorted to GND, 1 start without short circuit
ERRIO = "ERRIO"  # 0, 1 write/read error in/output ??? sets errio either 1 or 0, reports errio:ok
STARTMODE = "STARTMODE"  # 0, 1; 0=pause pump after switchon, 1=start immediatley with previous set flow rate
# no idea what these do...
ADJ10 = 'ADJ10'  # 100-2000
ADJ50 = 'ADJ50'  # 100-2000
CORR10 = "CORR10"  # 0-300
CORR50 = "CORR50"  # 0-300

# RD only
EXTFLOW = "EXTFLOW?"
IMOTOR = "IMOTOR?"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS?"  # displays last 5 error codes

# WR only
EXTCONTR = "EXTCONTR:"  # 0, 1; 1= allows flow control via external analog input, 0 dont allow
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow


class KnauerPump(EthernetDevice):
    def __init__(self, address, port=KnauerCommunicationConstants.TCP_PORT.value, buffersize=KnauerCommunicationConstants.BUFFER_SIZE.value):
        super().__init__(address, port, buffersize)
        self.headtype
        self.set_minimum_pressure(pressure_in_bar=5)

    def communicate(self, message: str):
        """
        sends command and receives reply, deals with all communication based stuff and checks that the valve is of expected type
        :param message:
        :return: reply: str
        """

        # beware: I think the pumps want \n\r as end of message, the valves \r\n
        message = str(message)+'\n\r'
        reply = super()._send_and_receive_handler(message)
        if reply == "ERROR:1":
            CommandError('Invalid message sent to device. Message was: {}. Reply is {}'.format(message, reply))

        elif reply == "ERROR:2":
            ParameterError('Setpoint refused by device. Refer to manual for allowed values.  Message was: {}. '
                           'Reply is {}'.format(message, reply))

        elif ':OK' in reply:
            logging.info('setpoint successfully set')
        elif message[:-1] + ':' in reply:
            logging.info('setpoint successfully acquired, is ' + reply)
        return reply

    # read and write. write: append ":value", read: append "?"
    def message_constructor_dispatcher(self, message, setpoint: int = None, setpoint_range: tuple = None):
        if not setpoint:
            return self.communicate(message+"?")

        elif setpoint_range:
            if setpoint in range(*setpoint_range):
                return self.communicate(message+":"+str(setpoint))

            else:
                ParameterError('Internal check shows that setpoint provided ({}) is not in range({}). Refer to'
                           ' manual.'.format(setpoint, setpoint_range))
        else:
            return self.communicate(message + ":" + str(setpoint))

    def set_flow(self, setpoint: int = None):
        """

        :param setpoint: in µL/min
        :return: device answer
        """

        flow = self.message_constructor_dispatcher(FLOW, setpoint=setpoint, setpoint_range=(0, self.achievable_flow+1))
        logging.info('Flow of pump {} is set to {}, returns {}'.format(self.address, setpoint, flow))
        return flow

    @property
    def headtype(self):
        reply = int(self.message_constructor_dispatcher(HEADTYPE)[-2:])
        try:
            headtype=KnauerPumpHeads(reply)
        except ValueError as e:
            raise KnauerError('It seems you\'re trying instantiate an unknown device/unknown pump type as Knauer Pump.'
                  'Only Knauer Azura Compact is supported') from e

        logging.info('Headtype of pump {} is {}'.format(self.address, headtype))
        self.achievable_pressure, self.achievable_flow = (400, 10000) if headtype == KnauerPumpHeads.FLOWRATE_TEN_ML \
            else (150, 50000)
        return headtype

    @headtype.setter
    def headtype(self, setpoint: KnauerPumpHeads):
        reply = self.message_constructor_dispatcher(HEADTYPE, setpoint=setpoint.value)
        self.achievable_pressure, self.achievable_flow = (400, 10000) if setpoint == KnauerPumpHeads.FLOWRATE_TEN_ML \
            else (150, 50000)
        logging.info('Headtype of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))
        return setpoint

    def set_minimum_pressure(self, pressure_in_bar=None):

        command = PMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMIN50

        reply = self.message_constructor_dispatcher(command, setpoint=pressure_in_bar,
                                                    setpoint_range=(0, self.achievable_pressure+1))
        logging.info('Minimum pressure of pump {} is set to {}, returns {}'.format(self.address, pressure_in_bar, reply))
        return reply

    def set_maximum_pressure(self, pressure_in_bar=None):
        command = PMAX10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMAX50

        reply = self.message_constructor_dispatcher(command, setpoint=pressure_in_bar,
                                                    setpoint_range=(0, self.achievable_pressure + 1))
        logging.info('Maximum pressure of pump {} is set to {}, returns {}'.format(self.address, pressure_in_bar, reply))

        return reply

    def set_minimum_motor_current(self, setpoint=None):
        command = IMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = self.message_constructor_dispatcher(command, setpoint=setpoint,
                                                    setpoint_range=(0, 101))
        logging.info('Minimum motor current of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))

        return reply

    def set_start_level(self, setpoint=None):
        reply = self.message_constructor_dispatcher(STARTLEVEL, setpoint=setpoint, setpoint_range= (0, 2))
        logging.info('Start level of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))

        return reply

    def set_start_mode(self, setpoint=None):
        """

        :param setpoint: 0 pause pump after switch on. 1 switch on immediately with previously selected flow rate
        :return: device message
        """
        if setpoint in (0, 1):
            reply= self.message_constructor_dispatcher(STARTMODE, setpoint=setpoint)
            logging.info('Start mode of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))
            return reply
        else:
            logging.warning('Supply binary value')

    def set_adjusting_factor(self, setpoint: int = None):
        command = ADJ10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = self.message_constructor_dispatcher(command, setpoint=setpoint, setpoint_range=(0,2001))
        logging.info('Adjusting factor of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))

        return reply

    def set_correction_factor(self, setpoint=None):
        command = CORR10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = self.message_constructor_dispatcher(command, setpoint=setpoint, setpoint_range=(0,301))
        logging.info('Correction factor of pump {} is set to {}, returns {}'.format(self.address, setpoint, reply))

        return reply

    # read only
    def read_pressure(self):
        reply = int(self.communicate(PRESSURE)[9:])
        logging.info(f'Pressure reading of pump {self.address} returns {reply} bar')

        return reply

    def read_extflow(self):
        reply =int(self.communicate(EXTFLOW)[8:])
        logging.info('Extflow reading of pump {self.address} returns {reply}')
        return reply

    def read_errors(self):
        reply = self.communicate(ERRORS)
        logging.info('Error reading of pump {} returns {}'.format(self.address, reply))
        return reply

    def read_motor_current(self):
        reply = self.communicate(IMOTOR)
        logging.info('Motor current reading of pump {} returns {}'.format(self.address, reply))
        return reply

    #TODO run flag
    # write only
    def start_flow(self):
        reply = self.communicate(PUMP_ON)
        if reply != "ON:OK":
            raise CommandError
        else:
            logging.info('Pump switched on')

    def stop_flow(self):
        reply = self.communicate(PUMP_OFF)
        if reply != "OFF:OK":
            raise CommandError
        else:
            logging.info('Pump switched off')

    def set_local(self, param: int):
        if param in (0, 1):
            logging.info('Pump {} set local {}'.format(self.address, param))
            return self.communicate(LOCAL + ':' + str(param))
        else:
            logging.warning('Supply binary value')

    def set_remote(self, param: int):
        if param in (0, 1):
            logging.info('Pump {} set remote {}'.format(self.address, param))
            return self.communicate(REMOTE + ':' + str(param))
        else:
            logging.warning('Supply binary value')

    # no idea what this exactly does...
    def set_errio(self, param: int):
        if param in (0, 1):
            logging.info('Pump {} set errio {}'.format(self.address, param))
            return self.communicate(ERRIO + ':' + str(param))
        else:
            logging.warning('Supply binary value')

    def set_extcontrol(self, param: int):
        if param in (0,1):
            logging.info('Pump {} set extcontrol {}'.format(self.address, param))
            return self.communicate(EXTCONTR+':'+str(param))
        else:
            logging.warning('Supply binary value')

    def close_connection(self):
        self.sock.close()
        logging.info('Connection with {} closed'.format(self.address))


# Valve

# send number to move to
# returns '?' for out of range and 'OK' für done
# E für Error
# return E0: ventilposition wurde nicht geändert
# return E1: Motorstrom zu hoch
# V für Version,
# H für unbekannt, maybe HOME?
# N returns E1,
# P positions returns actual position
# R returns OK, maybe Reverse?,
# S retunrs S:0000002D,
# T returns VALVE TYPE, TYPE is LI, 6, 12, 16

# ALWAYS APPEND NEWLINE r\n\, answer will be answer\n

# TODO pump needs a way to delete ERROR


if __name__ == "__main__":
    p = KnauerPump('192.168.1.119')