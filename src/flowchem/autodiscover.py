"""This module is used to autodiscover any supported devices connected to the PC."""
from pathlib import Path

import aioserial
import rich_click as click
import serial.tools.list_ports as list_ports
from loguru import logger

from flowchem.devices.hamilton.ml600_finder import ml600_finder
from flowchem.devices.harvardapparatus.elite11_finder import elite11_finder
from flowchem.devices.huber.chiller_finder import chiller_finder
from flowchem.devices.knauer.knauer_finder import knauer_finder

SERIAL_DEVICE_INSPECTORS = (ml600_finder, elite11_finder, chiller_finder)


def inspect_serial_ports() -> set[str]:
    """Search for known devices on local serial ports and generate config stubs."""
    port_available = [comport.device for comport in list_ports.comports()]
    logger.info(
        f"Found the following serial port(s) on the current device: {port_available}"
    )

    dev_found_config: set[str] = set()
    # Loop each serial port
    for serial_port in port_available:
        logger.info(f"Looking for known devices on {serial_port}...")
        # Check if the serial port is available (i.e. not already open)
        try:
            port = aioserial.Serial(serial_port)
            port.close()
        except OSError:
            logger.info(f"Skipping {serial_port} (cannot be opened: already in use?)")
            continue

        # For each port try all functions that can detect serial port devices
        for inspector in SERIAL_DEVICE_INSPECTORS:
            # a list of config is return by the inspector, if len(config) == 0 then it is falsy
            if config := inspector(serial_port):
                dev_found_config.update(config)
                break
        logger.info(f"No known device found on {serial_port}")

    return dev_found_config


def inspect_eth(source_ip):
    """Search for known devices on ethernet and generate config stubs."""
    logger.info("Starting ethernet detection")

    return knauer_finder(source_ip)


@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file",
    show_default=True,
    default="flowchem_config.toml",
)
@click.option(
    "--overwrite",
    "-w",
    is_flag=True,
    help="Overwrite existing configuration file if present",
)
@click.option("--safe-only", "-s", is_flag=True, help="Run only safe modules.")
@click.option(
    "--assume-yes",
    "--yes",
    "-y",
    is_flag=True,
    help="Assume 'yes' as answer to all prompts and run non-interactively.",
)
@click.option(
    "--source-ip",
    help="Source IP for broadcast packets. (Relevant if multiple eth interface are available)",
    default=None,
)
def main(output, overwrite, safe_only, assume_yes, source_ip):
    """Auto-find devices connected to the current PC."""
    # Validate output location
    if Path(output).exists() and not overwrite:
        logger.error(
            f"Output file `{output}` already existing! Use `--overwrite` to replace it."
        )
        return

    # Ask confirmation for serial communication
    if not safe_only and not assume_yes:
        logger.warning(
            "The autodiscover include modules that involve communication over serial ports."
        )
        logger.warning("These modules are *not* guaranteed to be safe!")
        logger.warning(
            "Unsupported devices could be placed in an unsafe state as result of the discovery process!"
        )
        assume_yes = click.confirm(
            "Do you want to include the search for serial devices?"
        )

    # Search serial devices
    if not safe_only and assume_yes:
        serial_config = inspect_serial_ports()
    else:
        serial_config = set()

    # Search ethernet devices
    eth_config = inspect_eth(source_ip)

    # Print results
    if not serial_config and not eth_config:
        logger.error(
            f"No device found! The output file `{output}` will not be created."
        )
        return
    logger.info(f"Found {len(serial_config) + len(eth_config)} devices!")

    # Print configuration
    configuration = "".join(serial_config) + "".join(eth_config)
    logger.info(
        f"The following configuration will be written to `{output}:\n{configuration}"
    )

    # Write to file
    with Path(output).open("w", encoding="utf-8") as f:
        f.write(configuration)
    logger.info(f"Configuration written to `{output}`!")


if __name__ == "__main__":
    main()
