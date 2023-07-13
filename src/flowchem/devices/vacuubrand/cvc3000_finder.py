"""This module is used to discover the serial address of any CVC3000 connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.vacuubrand.cvc3000 import CVC3000
from flowchem.utils.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def cvc3000_finder(serial_port) -> list[str]:
    """Try to initialize a CVC3000 on every available COM port."""
    logger.debug(f"Looking for CVC3000 on {serial_port}...")

    try:
        cvc = CVC3000.from_config(port=serial_port)
    except InvalidConfiguration:
        return []

    try:
        asyncio.run(cvc.initialize())
    except InvalidConfiguration:
        cvc._serial.close()
        return []

    logger.info(f"CVC3000 {cvc.component_info.version} found on <{serial_port}>")

    return [
        dedent(
            f"""
            [device.cvc-{cvc._device_sn}]
            type = "CVC3000"
            port = "{serial_port}"\n\n""",
        ),
    ]
