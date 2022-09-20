""" Shell script executor """
from pathlib import Path

import rich_click as click
import uvicorn
from flowchem import __version__
from flowchem.server.api_server import create_server_from_file
from loguru import logger


@click.argument("device_config", type=click.Path(), required=True)
@click.version_option()
@click.command()
def main(device_config):
    """Flowchem CLI entry point."""
    print(f"Starting flowchem v. {__version__}!")
    logger.add(Path("./flowchem.log"))
    logger.debug(f"Starting server with configuration file: '{device_config}'")

    myapp = create_server_from_file(Path(device_config))
    uvicorn.run(myapp)


if __name__ == "__main__":
    main()
