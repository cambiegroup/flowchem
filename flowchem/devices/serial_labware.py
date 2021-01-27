# coding=utf-8
# !/usr/bin/env python
"""
"serial_labware" -- Generic base class for communicating with lab equipment via serial connection
===================================

.. module:: serial_labware
   :platform: Windows
   :synopsis: Generic base class to control lab equipment via serial.
   :license: BSD 3-clause
.. moduleauthor:: Sebastian Steiner <s.steiner.1@research.gla.ac.uk>

(c) 2018 The Cronin Group, University of Glasgow

This provides a generic python class for safe serial communication
with various lab equipment over serial interfaces (RS232, RS485, USB)
by sending command strings. This parent class handles establishing
a connection as well as sending and receiving commands.
Based on code originally developed by Stefan Glatzel.

For style guide used see http://xkcd.com/1513/
"""

import logging
import re
import socket
import sys
import threading
from functools import wraps
from queue import Empty, Queue
from time import sleep, time

import serial


def command(func):
    """
    Decorator for command_set execution. Checks if the method is called in the same thread as the class instance,
    if so enqueues the command_set and waits for a reply in the reply queue. Else it concludes it must be the command
    handler thread and actually executes the method. This way methods in the child classes need to be written
    just once and decorated accordingly.

    Returns:
        decorated method
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        device_instance = args[0]
        if threading.get_ident() == device_instance.current_thread:
            command_set = [func, args, kwargs]
            device_instance.command_queue.put(command_set)
            while True:
                try:
                    return device_instance.reply_queue.get(timeout=10)
                    # Setting timeout to 10 secs is a temporary change to fix the issue when library hangs
                    # if exception is thrown from the function wrapped with @command decorator and get_return=True
                    # Without timeout here's what happens:
                    # wrapper puts the wrapped function in the queue with device_instance.command_queue.put(command_set) and then main thread blocks on reply_queue.get()
                    # Then a command execution thread fetches & executes the function where exception occurs, so potentially no command is sent to serial port & no reply can be expected
                    # But main thread keeps blocked forever on reply_queue.get() because it has no clue that command has not been actually sent
                except Empty:
                    raise Empty("Reply queue timeout!") from None
        else:
            return func(*args, **kwargs)

    return wrapper


class SerialDevice:
    """
    This is a generic parent class handling serial communication with lab equipment. It provides
    methods for opening and closing connections as well as a keepalive. It works by spawning a
    daemon thread which periodically checks a queue for commands. If no commands are enqueued,
    a keepalive method is executed periodically. Replies are put in their own reply queue where
    they can be retrieved at any time.
    """
    def __init__(self, address=None, port=None, mode="serial", device_name=None, connect_on_instantiation=False, soft_fail_for_testing=False):
        """
        Initializer of the SerialDevice class

        Args:
            port (str): The port name/number of the serial device
            address (str): The IP address in case the labware is connected through Ethernet-to-Serial adapter
            device_name (str): A descriptive name for the device, used mainly in debug prints
            soft_fail_for_testing (bool): (optional) determines if an invalid serial port raises an error or merely
                logs a message. Default: Off
        """
        # note down current thread number
        self.current_thread = threading.get_ident()
        self.disconnect_requested = threading.Event()
        self.disconnect_requested.clear()
        # implement class logger
        #FIXME this has to be re-done, no hard-coded logger names
        self.logger = logging.getLogger("main_logger.serial_device_logger")
        # spawn queues
        self.command_queue = Queue()
        self.reply_queue = Queue()
        
        # DEBUG testing switch, to allow soft-fails instead of exceptions
        self.__soft_fail_for_testing = soft_fail_for_testing

        # Mutex for thread-safe access to connection read/write functions
        self._connection_lock = threading.RLock()

        # device name and port
        self.device_name = device_name
        self.port = port
        self.address = address

        # syntax of a returned answer, to be overridden by child classes
        self.answer_pattern = re.compile("(.*)")  # any number of any character, in one group

        # initialise last time (for non blocking wait
        self.last_time = time()

        # Connection object
        self.__connection = None
        
        # Command format settings
        # hasattr() is used not to override the attributes that might have already been set in the child class before activating this with super().__init__()
        if not hasattr(self, "command_termination"): self.command_termination = '\r\n'
        if not hasattr(self, "standard_encoding"): self.standard_encoding = 'UTF-8'

        # Serial connection settings
        if not hasattr(self, "baudrate"): self.baudrate = 9600
        if not hasattr(self, "bytesize"): self.bytesize = serial.EIGHTBITS
        if not hasattr(self, "parity"): self.parity = serial.PARITY_NONE
        if not hasattr(self, "stopbits"): self.stopbits = serial.STOPBITS_ONE
        if not hasattr(self, "timeout"): self.timeout = 1
        if not hasattr(self, "xonxoff"): self.xonxoff = False
        if not hasattr(self, "rtscts"): self.rtscts = False
        if not hasattr(self, "write_timeout"): self.write_timeout = None
        if not hasattr(self, "dsrdtr"): self.dsrdtr = False
        if not hasattr(self, "inter_byte_timeout"): self.inter_byte_timeout = None

        # I/O delays
        if not hasattr(self, "write_delay"): self.write_delay = 0
        if not hasattr(self, "read_delay"): self.read_delay = 0
        
        # Set device mode
        self.mode = mode if mode is not None else "serial"
        if self.mode == "serial":
            self.port = port
        elif self.mode == "ethernet":
            self.port = 5000 if port is None else port
        else:
            raise ValueError("Unknown connection mode specified!")
        
        if connect_on_instantiation is True:
            self.open_connection()

    def __command_handler_daemon(self):
        """
        Daemon thread for relaying any commands to the device. The "possession" of the serial port and therefore
        any actual communication with the device is relegated to its own thread, partially to free up the main
        thread for more important stuff, partially to allow for implementation of watchdog keepalive calls,
        which would be tremendously tricky to do from the main thread.

        This private function polls the command_queue for any commands to send. If no commands are queued,
        a keepalive method is executed. Any replies received from the device are enqueued into reply_queue for
        further processing.
        """
        while True:
            if self.disconnect_requested.is_set():
                self.logger.debug("Stop requested, command handler exiting.")
                break
            try:
                if not self.command_queue.empty():
                    command_item = self.command_queue.get()
                    method = command_item[0]
                    arguments = command_item[1]
                    keywordarguments = command_item[2]
                    reply = method(*arguments, **keywordarguments)
                    self.reply_queue.put(reply)
                else:
                    self.keepalive()
            except:
                # workaround if something goes wrong with the serial connection
                # future me will certainly not hate past me for this...
                # but current other one hates you for that been done that way!
                err_msg = f"Error while running {method} - {sys.exc_info()[1]}"
                self.logger.critical(err_msg)
                if self.mode == 'serial':
                    self.__connection.flush()
                # Purge the queues
                while not self.command_queue.empty():
                    self.command_queue.get()
                while not self.reply_queue.empty():
                    self.reply_queue.get()

    def launch_command_handler(self):
        self.command_handler = threading.Thread(target=self.__command_handler_daemon, name=f"{self.device_name}_command_handler", daemon=True)
        self.command_handler.start()

    def open_connection(self):
        """
        Opens the serial connection to the device.
        If a connection is already open it is closed and then a connection is re-established with the current settings
        """
        self.disconnect_requested.clear()
        # Purge the queues
        while not self.command_queue.empty():
            self.command_queue.get()
        while not self.reply_queue.empty():
            self.reply_queue.get()
        if self.mode == 'serial':
            if self.__connection is not None and self.__connection.isOpen():
                self.logger.info("Already connected!")
                return
            try:
                self.__connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=self.timeout,
                    xonxoff=self.xonxoff,
                    rtscts=self.rtscts,
                    write_timeout=self.write_timeout,
                    dsrdtr=self.dsrdtr,
                    inter_byte_timeout=self.inter_byte_timeout
                )
                self.launch_command_handler()
                return True  # announce success
            except (AttributeError, FileNotFoundError, serial.SerialException) as e:
                # allowing for soft fail in test modes, this will allow an outer script to continue, even if an
                # invalid port was passed
                if not self.__soft_fail_for_testing:
                    # in normal use just raise exception again
                    raise
                else:
                    # soft-fail error message
                    self.logger.debug(f"ERROR: The connection to the serial device could not be established: {e}")
                    return False  # announce failure
        elif self.mode == 'ethernet':
            # in case 'address' was provided and 'mode' was set to "socket"
            # create a socket connection
            self.__connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set socket timeout
            self.__connection.settimeout(self.timeout)
            try:
                # connecting to the provided address
                if self.address is None:
                    raise ValueError("Invalid address provided for ethernet connection mode!")
                self.__connection.connect((self.address, self.port))
                self.launch_command_handler()
                # announce success
                return True
            except OSError as e:
                if not self.__soft_fail_for_testing:
                    # in normal use just raise exception again
                    raise
                else:
                    # soft-fail error message
                    self.logger.debug(f"ERROR: The connection to the serial device could not be established: {e}")
                    return False  # announce failure
     
    def close_connection(self):
        """
        Stops command handler and closes the connection.
        """
        self.logger.debug("Stopping command handler...")
        self.disconnect_requested.set()
        self.command_handler.join()
        self.logger.debug("Command handler stopped...")
        if self.__connection is not None:
            self.__connection.close()
            # That line would prevent reconnection - open_connection fails if __connection is set to None
            #self.__connection = None
            return True
        else:
            self.logger.info("Device not yet connected.")
            return False  # announce failure


    def send_message(self, message, get_return=False, return_pattern=None, multiline=False, num_retries=3):
        """
        Method for sending messages to the device. This method needs to be publicly accessible, otherwise
        child classes can't use it. This method does not do a consistency check on the arguments passed to it,
        since they may vary wildly. Therefore such a check must be performed before calling send_message!

        Args:
            message (str): The message string. No checks are performed on the message and it is just passed on
            get_return (bool): Are you expecting a return message?
            return_pattern (_sre.SRE_Pattern): Passes on a regex pattern to check the returned message against
            multiline (bool): Are you expecting a return message spanning multiple lines?
                (not evaluated if get_return is False)
            num_retries (int): On failure, the number of re-connection attempts after which to give up

        Returns:
            (conditional)
            - returns "True" if no message is expected back
            - does a call back to "__receive_message" and passes on "the return pattern"
            - returns -1 if send message fails
        """
        # send the message and encode it according to the standard settings found in __init__
        # Hint: "{}".format(message) auto converts message to string in case it was something else, so no type checking
        # retry loop
        self.logger.debug(f"Sending command {message}")
        while True:
            try:
                sleep(self.write_delay)
                # Acquire lock
                self._connection_lock.acquire()
                # If we are to read reply from the device just after issuing the command - flush input buffer
                if get_return is True:
                    if self.mode == "serial":
                        self.__connection.reset_input_buffer()
                        self.logger.debug("Reset input buffer before sending command.")
                if self.mode == "serial":
                    self.__connection.write(f"{message}{self.command_termination}".encode(self.standard_encoding))
                else:
                    self.__connection.sendall(f"{message}{self.command_termination}".encode(self.standard_encoding))
                self.logger.debug("Command  %s sent.", message)
                sleep(self.read_delay)
                self._connection_lock.release()
                break
            # OSError here is a catch-all fallback for socket operations
            except (serial.SerialException, OSError) as e:
                # Release lock
                self._connection_lock.release()
                if num_retries > 0:
                    # reconnect and try again
                    num_retries -= 1
                    self.close_connection()
                    self.open_connection()
                    continue
                elif not self.__soft_fail_for_testing:
                    # just raise the exception again when not in test mode
                    raise
                else:
                    self.logger.error(f"Error: Unexpected error while writing to connection. Error Message: {e}")
                    self._connection_lock.release()
                    break
        # if the user specified that a return message is expected
        if get_return:
            # call back to __receive_message and passing on of the expected regex pattern
            self.logger.debug("Reply requested, waiting for device...")
            reply = self.__receive_message(return_pattern=return_pattern, multiline=multiline)
            return reply
        else:
            return True

    def __receive_message(self, return_pattern=None, multiline=False):
        """
        Protected member function that is the sole responsible for actually receiving messages from the device.
            This isn't exactly the pythonic way of doing thing (protected member functions should be _ not __).
            However, two leading __ actually prevents the function to be called from the outside (as opposed to just
            raising a flag says "you're accessing a protected member function".
        Pro-Tip: (due to Python weirdness) A savvy user can still gain access to thus protected functions via
            {InstanceName}._{ClassName}__{FunctionName}

        Args:
            return_pattern (_sre.SRE_Pattern): Passes on a regex pattern to check the returned message against
            multiline (bool): Are you expecting a return message spanning multiple lines?

        Returns:
            answer (str or list of str): If no return pattern is specified, the stripped answer string is returned. If
                a pattern is passed, a list of the captured groups is returned instead
        """
        try:
            # checking if a connection is there
            if self.__connection is not None:
                # Get data from connection
                # If multiple lines are expected, keep reading lines until no more lines come in
                # That's always the case for socket connection because data is read back in chunks
                if multiline or self.mode == "ethernet":
                    answer = ""
                    with self._connection_lock:
                        while True:
                            if self.mode == "serial":
                                line = self.__connection.readline()
                                if line:
                                    try:
                                        try:
                                            answer += line.decode(self.standard_encoding)
                                        except UnicodeDecodeError:
                                            answer += line.decode('latin1')
                                    except UnicodeDecodeError:
                                        self.logger.warning("Failed to decode reply. Raw reply: %s", answer)
                                        answer += line
                                else:
                                    break
                            # Ethernet connection
                            else:
                                # Read data from socket
                                try:
                                    chunk = self.__connection.recv(4096)
                                    while chunk:
                                        answer += chunk.decode()
                                        chunk = self.__connection.recv(4096)
                                except socket.timeout:
                                    break
                # if just one line is expected, just read one line (faster than always waiting for the timeout)
                else:
                    with self._connection_lock:
                        answer = self.__connection.readline()
                    # decoding the answer using the standard settings from __init__
                    try:
                        try:
                            answer = answer.decode(self.standard_encoding)
                        except UnicodeDecodeError:
                            answer = answer.decode('latin1')
                    except UnicodeDecodeError:
                        self.logger.warning("Failed to decode reply. Raw reply: %s", answer)
                
                # If we got an empty line, this is probably not what user asked for
                if answer == "":
                    raise ValueError("No response received!")
                # Otherwise log reply
                self.logger.debug("Received reply: %s", answer)
                
                # Handle RegEx validation
                if return_pattern is not None:
                    try:
                        answer = re.match(pattern=return_pattern, string=answer).groups()
                        if answer is None:
                            self.logger.critical(
                                "Value Error. Serial device did not return correct return code. Send: \"{0}\". "
                                "Received: \"{1}\".".format(return_pattern, answer)
                            )
                            if self.__soft_fail_for_testing:
                                return answer.strip()
                            else:
                                raise ValueError(
                                    "Value Error. Serial device did not return correct return code. Send: \"{0}\". "
                                    "Received: \"{1}\".".format(return_pattern, answer)
                                )
                        return answer
                    except AttributeError:
                        raise ValueError("The return code you specified was not a valid regular expression object!")
                else:
                    # if no return code checking was requested, just return the read value
                    return answer.strip()
            else:
                raise Exception("Error. No connection to the device")
        except Exception as e:
            # This is not very elegant, but lets the user know that the device failed while retaining the error
            # information
            raise Exception(f"Serial device message receive failed. Error Message: {e}\n{e.__traceback__}")

    def non_blocking_wait(self, callback, interval):
        """
        Simple non-blocking wait function crafted after the Arduino Blink Without Delay example. Checks whether the
        time elapsed since the last callback is greater than or equal to the interval. If so, the callback method
        is returned and the time updated.

        Args:
            callback: function or method to be executed
            interval (int): wait time in seconds

        Returns:
            callback if interval has elapsed, None otherwise
        """
        if time() >= (self.last_time + interval):
            self.last_time = time()
            return callback()
        else:
            return None

    def keepalive(self):
        """
        Dummy keepalive method. This is just a stand-in for whatever keepalive operation needs to be performed
        on the device, meant to be overridden in the actual child class.
        """
        sleep(0.1)

    #FIXME potentially duplicates close_connection()
    def disconnect(self):
        """
        Disconnect from device. This method needs to be called to reconnect
        to the device within the same Python process.
        """
        self.close_connection()
