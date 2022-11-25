"""This module is used to discover the serial address of any Vapourtec device connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices import R4Heater
from flowchem.utils.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def r4_finder(serial_port) -> list[str]:
    """Try to initialize an R4Heater on every available COM port."""
    logger.debug(f"Looking for R4Heaters on {serial_port}...")
    # Static counter for device type across different serial ports
    if "counter" not in r4_finder.__dict__:
        r4_finder.counter = 0  # type: ignore

    try:
        r4 = R4Heater(port=serial_port)
    except InvalidConfiguration as ic:
        logger.error("config")
        raise ic
        return []

    try:
        asyncio.run(r4.initialize())
    except InvalidConfiguration:
        r4._serial.close()
        return []

    if r4.metadata.version:
        logger.info(f"R4 version {r4.metadata.version} found on <{serial_port}>")
        # Local variable for enumeration
        r4_finder.counter += 1  # type: ignore
        cfg = f"[device.r4-heater-{r4_finder.counter}]"  # type:ignore
        cfg += dedent(
            f"""
        type = "R4Heater"
        port = "{serial_port}"\n\n"""
        )
    else:
        cfg = ""

    return [cfg]
