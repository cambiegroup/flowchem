"""This module is used to discover the serial address of any ML600 connected to the PC."""
import asyncio

import aioserial
import serial.tools.list_ports
from flowchem.devices.Hamilton.ML600 import HamiltonPumpIO
from flowchem.devices.Hamilton.ML600 import InvalidConfiguration
from loguru import logger


def ml600_finder():
    """Try to initialize an ML600 on every available COM port."""
    port_available = [comport.device for comport in serial.tools.list_ports.comports()]
    logger.info(f"Found the following serial port(s): {port_available}")

    # Ports connected to an ML600-looking device
    valid_ports = set()

    for serial_port in port_available:
        logger.info(f"Looking for pump on {serial_port}...")
        try:
            link = HamiltonPumpIO(aioserial.AioSerial(port=serial_port, timeout=0.1))
        except IOError:
            logger.warning(f"Cannot open {serial_port}!")
            continue

        try:
            asyncio.run(link.initialize())
            logger.info(f"{link.num_pump_connected} pump(s) found on <{serial_port}>")
            valid_ports.add(serial_port)
        except InvalidConfiguration:
            logger.info(f"No pumps found on {serial_port}.")

    return valid_ports


if __name__ == "__main__":
    ml600_pumps = ml600_finder()
    if len(ml600_pumps) > 0:
        logger.info(f"The following serial port are connected to ML600: {ml600_pumps}")
    else:
        logger.error("No ML600 pump found")
