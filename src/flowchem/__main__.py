"""
Entry-point module for the command line prefixer, called in case you use `python -m flowchem`.
Why does this file exist, and why `__main__`? For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""
import asyncio
import sys
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

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logger.info(f"Starting flowchem v. {__version__}!")
    if logfile:
        logger.add(Path(logfile))
    logger.debug(f"Starting server with configuration file: '{device_config_file}'")

    async def main_loop():
        """The loop must be shared between uvicorn and flowchem."""
        flowchem_instance = await run_create_server_from_file(
            Path(device_config_file), host=host
        )
        config = uvicorn.Config(
            flowchem_instance["api_server"],
            host=host,
            port=flowchem_instance["port"],
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
