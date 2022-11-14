"""
Entry-point module for the command line prefixer, called in case you use `python -m flowchem`.
Why does this file exist, and why `__main__`? For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""
from pathlib import Path

import rich_click as click
import uvicorn
from loguru import logger

from flowchem import __version__
from flowchem.server.api_server import run_create_server_from_file


@click.argument("device_config_file", type=click.Path(), required=True)
@click.option(
    "-l", "--log", "logfile", type=click.Path(), default=None, help="Save logs to file."
)
@click.option(
    "-h", "--host", "host", type=str, default="127.0.0.1", help="Server host."
)
@click.version_option()
@click.command()
def main(device_config_file, logfile, host):
    """
    Flowchem main program.

    Parse DEVICE_CONFIG_FILE and starts a server exposing the devices via RESTful API.
    """
    logger.info(f"Starting flowchem v. {__version__}!")
    if logfile:
        logger.add(Path(logfile))
    logger.debug(f"Starting server with configuration file: '{device_config_file}'")

    flowchem_instance = run_create_server_from_file(Path(device_config_file), host=host)
    uvicorn.run(
        flowchem_instance["api_server"],
        host=host,
        port=flowchem_instance["port"],
        timeout_keep_alive=3600,
    )


if __name__ == "__main__":
    main()
