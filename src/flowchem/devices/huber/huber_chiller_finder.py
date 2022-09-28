"""This module is used to discover the serial address of any ML600 connected to the PC."""
import asyncio

import rich_click as click
import serial.tools.list_ports
from loguru import logger

from flowchem.devices.huber.chiller import HuberChiller
from flowchem.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def chiller_finder():
    """Try to initialize an Elite11 on every available COM port."""
    port_available = [comport.device for comport in serial.tools.list_ports.comports()]
    logger.info(f"Found the following serial port(s): {port_available}")

    # Ports connected to an elite11-looking device
    valid_ports = set()

    for serial_port in port_available:
        logger.info(f"Looking for chiller on {serial_port}...")
        try:
            chill = HuberChiller.from_config(port=serial_port)
        except InvalidConfiguration:
            logger.warning(f"Cannot open {serial_port}!")
            continue

        try:
            asyncio.run(chill.initialize())
            sn = asyncio.run(chill.serial_number())
            logger.info(f"Chiller #{sn} found on <{serial_port}>")
            valid_ports.add(serial_port)
        except InvalidConfiguration:
            logger.info(f"No chiller found on {serial_port}.")

    return valid_ports


@click.command()
def main():
    """Autofind Huber Chiller. This is the entry point for the CLI app `huber-finder`."""
    huber_chillers = chiller_finder()
    if len(huber_chillers) > 0:
        logger.info(
            f"The following serial port are connected to huber chillers: {huber_chillers}"
        )
    else:
        logger.error("No Huber chiller found")


if __name__ == "__main__":
    main()
