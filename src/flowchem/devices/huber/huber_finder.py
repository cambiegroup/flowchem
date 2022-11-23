"""This module is used to discover the serial address of any Huber chiller connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.huber.chiller import HuberChiller
from flowchem.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def chiller_finder(serial_port) -> list[str]:
    """Try to initialize a Huber chiller on every available COM port."""
    logger.debug(f"Looking for Huber chillers on {serial_port}...")

    try:
        chill = HuberChiller.from_config(port=serial_port)
    except InvalidConfiguration:
        return []

    try:
        asyncio.run(chill.initialize())
    except InvalidConfiguration:
        chill._serial.close()
        return []

    logger.info(f"Chiller #{chill._device_sn} found on <{serial_port}>")

    return [
        dedent(
            f"""
            [device.huber-{chill._device_sn}]
            type = "HuberChiller"
            port = "{serial_port}"\n"""
        )
    ]
