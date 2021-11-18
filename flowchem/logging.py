import logging
from loguru import logger
from rich.logging import RichHandler
from rich.console import Console

logging.addLevelName(5, "TRACE")
logging.addLevelName(25, "SUCCESS")

logger.configure(
    handlers=[{"sink": RichHandler(console=Console(width=120)), "format": "{message}"}])
