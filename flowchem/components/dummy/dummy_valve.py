from typing import Optional

from loguru import logger
from flowchem.components.properties import Valve


class DummyValve(Valve):
    """
    A fake valve, used internally for testing.

    ::: danger
    This component can be used in a real protocol, although it doesn't actually exist.
    :::

    Arguments:
    - `port`: The available port names.
    - `name`: The name of the valve.
    """

    def __init__(self, name: Optional[str] = None, port: set = None):
        if port is None:
            port = {"position_1", "position_2", "position_3"}
        super().__init__(name=name, port=port)

    async def _update(self) -> None:
        logger.trace(f"Switching {self.name} to port {self.setting}")
