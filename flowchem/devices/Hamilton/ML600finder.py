"""
This module is used to discover the serial address of any ML600 connected to the PC.
"""
import logging
from flowchem.devices.Hamilton.ML600 import InvalidConfiguration, HamiltonPumpIO
import serial.tools.list_ports

log = logging.getLogger(__name__)


def ml600_finder():
    # List of all serial port available
    port_available = [comport.device for comport in serial.tools.list_ports.comports()]

    # Ports connected to an ML600-looking device
    valid_ports = set()

    for serial_port in port_available:
        try:
            link = HamiltonPumpIO(serial_port, hw_initialization=False)
            log.info(f"{link.num_pump_connected} pump(s) found on <{serial_port}>")
            valid_ports.add(serial_port)
        except InvalidConfiguration:
            log.debug(f"No pump found on {serial_port}")

    return valid_ports


if __name__ == "__main__":
    ml600_pumps = ml600_finder()
    if len(ml600_pumps) > 0:
        print(f"The following serial port are connected to ML600: {ml600_pumps}")
    else:
        print("No ML600 found")
