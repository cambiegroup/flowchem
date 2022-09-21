"""
This module is used to discover the serial address of any ML600 connected to the PC.
"""
import asyncio
import textwrap

import rich_click as click
import serial.tools.list_ports
from flowchem.devices.harvardapparatus.elite11 import Elite11InfuseOnly
from flowchem.devices.harvardapparatus.elite11 import HarvardApparatusPumpIO
from flowchem.exceptions import InvalidConfiguration
from loguru import logger


# noinspection PyProtectedMember
def elite11_finder() -> set:
    """Try to initialize an Elite11 on every available COM port."""
    port_available = [comport.device for comport in serial.tools.list_ports.comports()]
    logger.info(f"Found the following serial port(s): {port_available}")

    # Ports connected to an elite11-looking device
    valid_ports = set()
    config = ""

    for serial_port in port_available:
        logger.info(f"Looking for pump on {serial_port}...")
        try:
            link = HarvardApparatusPumpIO(port=serial_port)
            link._serial.write(b"\r\n")

            if link._serial.readline() == b"\n":
                valid_ports.add(serial_port)
                logger.info(f"Pump found on <{serial_port}>")

                pump = link._serial.readline().decode("ascii")
                if pump[0:2].isdigit():
                    address = int(pump[0:2])
                else:
                    address = 0

                test_pump = Elite11InfuseOnly(
                    link,
                    syringe_diameter="20 mm",
                    syringe_volume="10 ml",
                    address=address,
                )
                info = asyncio.run(test_pump.pump_info())

                p_type = (
                    "Elite11InfuseOnly" if info.infuse_only else "Elite11InfuseWithdraw"
                )

                config += textwrap.dedent(
                    f"""
                [device.my-elite11-pump{len(valid_ports)}]
                type = "{p_type}"
                port = "{serial_port}"
                address = {address}
                syringe_diameter = "XXX mm"
                syringe_volume = "YYY ml"

                """
                )
            else:
                logger.debug(f"No pump found on {serial_port}")
        except InvalidConfiguration:
            pass

    logger.info(f"Pump configuration stub:\n{config}")

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
