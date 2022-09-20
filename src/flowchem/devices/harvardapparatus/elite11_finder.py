"""
This module is used to discover the serial address of any ML600 connected to the PC.
"""
import rich_click as click
import serial.tools.list_ports
from loguru import logger

from flowchem.devices.harvardapparatus.elite11 import (
    HarvardApparatusPumpIO,
)
from flowchem.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def elite11_finder():
    """Try to initialize an Elite11 on every available COM port."""
    port_available = [comport.device for comport in serial.tools.list_ports.comports()]
    logger.info(f"Found the following serial port(s): {port_available}")

    # Ports connected to an elite11-looking device
    valid_ports = set()

    for serial_port in port_available:
        logger.info(f"Looking for pump on {serial_port}...")
        try:
            link = HarvardApparatusPumpIO(port=serial_port)
            link._serial.write(b"\r\n")

            if link._serial.readline() == b"\n":
                valid_ports.add(serial_port)
                logger.info(f"Pump found on <{serial_port}>")

                pump = link._serial.readline().decode("ascii")
                try:
                    int(pump[0:2])
                    logger.info(f"Pump address is {pump[0:2]}!")
                except ValueError:
                    logger.info(f"Single pump, not part of daisy chain.")
            else:
                logger.debug(f"No pump found on {serial_port}")
        except InvalidConfiguration:
            pass

    return valid_ports


@click.command()
def main():
    elite11_pumps = elite11_finder()
    if len(elite11_pumps) > 0:
        logger.info(
            f"The following serial port are connected to Elite11: {elite11_pumps}"
        )
    else:
        logger.error("No Elite11 pump found")


if __name__ == "__main__":
    main()
