"""
This module is used to discover the serial address of any ML600 connected to the PC.
"""
import logging
from flowchem.devices.Hamilton.ML600 import InvalidConfiguration, HamiltonPumpIO

log = logging.getLogger(__name__)

valid_ports = set()


for serial_port in port_available:
    try:
        link = HamiltonPumpIO(serial_port, hw_initialization=False)

    except InvalidConfiguration:
        log.debug(f"No pump found on {serial_port}")



if __name__ == "__main__":
