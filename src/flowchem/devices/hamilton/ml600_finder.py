"""This module is used to discover the serial address of any ML600 connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.hamilton.ml600 import InvalidConfiguration
from flowchem.devices.hamilton.ml600 import ML600


def ml600_finder(serial_port) -> set[str | None]:
    """Try to initialize an ML600 on every available COM port."""
    logger.debug(f"Looking for ML600 pumps on {serial_port}...")
    # Static counter for device type across different serial ports
    if "counter" not in ml600_finder.__dict__:
        ml600_finder.counter = 0
    dev_config = set()

    try:
        link = ML600.HamiltonPumpIO.from_config({"port": serial_port})
    except InvalidConfiguration:
        return dev_config

    try:
        asyncio.run(link.initialize(hw_initialization=False))
    except InvalidConfiguration:
        # This is necessary only on failure to release the port for the other inspector
        link._serial.close()
        return dev_config

    for count in range(link.num_pump_connected):
        logger.info(f"Pump ML600 found on <{serial_port}> address {count + 1}")

        ml600_finder.counter += 1
        dev_config.add(
            dedent(
                f"""\n\n[device.ml600-{ml600_finder.counter}]
        type = "ML600"
        port = "{serial_port}"
        address = {count + 1}
        syringe_volume = "XXX ml" # Specify syringe volume here!\n"""
            )
        )

    return dev_config
