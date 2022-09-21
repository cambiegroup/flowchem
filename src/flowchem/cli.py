""" Shell script executor """
from pathlib import Path

import rich_click as click
import uvicorn
from flowchem import __version__
from flowchem.server.api_server import create_server_from_file
from loguru import logger


@click.argument("device_config_file", type=click.Path(), required=True)
@click.option(
    "-l", "--log", "logfile", type=click.Path(), default=None, help="Save logs to file."
)
@click.version_option()
@click.command()
def main(device_config_file, logfile):
    """Flowchem main program.

    Parse DEVICE_CONFIG_FILE and starts a server exposing the devices via RESTful API."""
    print(f"Starting flowchem v. {__version__}!")
    if logfile:
        logger.add(Path(logfile))
    logger.debug(f"Starting server with configuration file: '{device_config_file}'")

    myapp = create_server_from_file(Path(device_config_file))
    uvicorn.run(myapp)


if __name__ == "__main__":
    main()
