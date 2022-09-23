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
@click.option(
    "-h", "--host", "host", type=str, default="127.0.0.1", help="Server host."
)
@click.option("-p", "--port", "port", type=int, default=8000, help="Server port.")
@click.version_option()
@click.command()
def main(device_config_file, logfile, host, port):
    """Flowchem main program.

    Parse DEVICE_CONFIG_FILE and starts a server exposing the devices via RESTful API."""
    print(f"Starting flowchem v. {__version__}!")
    if logfile:
        logger.add(Path(logfile))
    logger.debug(f"Starting server with configuration file: '{device_config_file}'")

    myapp = create_server_from_file(Path(device_config_file))
    uvicorn.run(myapp, host=host, port=port, timeout_keep_alive=3600)


if __name__ == '__main__':
    main()