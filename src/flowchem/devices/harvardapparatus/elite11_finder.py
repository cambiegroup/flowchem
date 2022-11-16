"""This module is used to discover the serial address of any Elite11 connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.harvardapparatus.elite11 import Elite11
from flowchem.devices.harvardapparatus.elite11 import HarvardApparatusPumpIO
from flowchem.exceptions import InvalidConfiguration


# noinspection PyProtectedMember
def elite11_finder(serial_port) -> set[str]:
    """Try to initialize an Elite11 on every available COM port. [Does not support daisy-chained Elite11!]"""
    logger.debug(f"Looking for Elite11 pumps on {serial_port}...")
    # Static counter for device type across different serial ports
    if "counter" not in elite11_finder.__dict__:
        elite11_finder.counter = 0  # type: ignore

    try:
        link = HarvardApparatusPumpIO(port=serial_port)
    except InvalidConfiguration:
        # This is necessary only on failure to release the port for the other inspector
        return set()

    # Check for echo
    link._serial.write(b"\r\n")
    if link._serial.readline() != b"\n":
        # This is necessary only on failure to release the port for the other inspector
        link._serial.close()
        return set()

    # Parse status prompt
    pump = link._serial.readline().decode("ascii")
    if pump[0:2].isdigit():
        address = int(pump[0:2])
    else:
        address = 0

    try:
        test_pump = Elite11(
            link,
            syringe_diameter="20 mm",
            syringe_volume="10 ml",
            address=address,
        )
        info = asyncio.run(test_pump.pump_info())
    except InvalidConfiguration:
        # This is necessary only on failure to release the port for the other inspector
        link._serial.close()
        return set()

    p_type = "Elite11InfuseOnly" if info.infuse_only else "Elite11InfuseWithdraw"
    logger.info(f"Pump {p_type} found on <{serial_port}>")

    elite11_finder.counter += 1  # type: ignore
    return set(
        dedent(
            f"\n\n[device.elite11-{elite11_finder.counter}]"  # type:ignore
            f"""type = "{p_type}
               port = "{serial_port}"
               address = {address}
               syringe_diameter = "XXX mm" # Specify syringe diameter!
               syringe_volume = "YYY ml" # Specify syringe volume!\n"""
        )
    )
