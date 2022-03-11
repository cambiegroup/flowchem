from typing import Optional

from loguru import logger

from flowchem.components.properties import TempControl


class DummyTempControl(TempControl):
    """
    A fake temp controller, used internally for testing.

    ::: danger
    This component can be used in a real protocol, although it doesn't actually exist.
    :::

    Arguments:
    - `port`: The available port names.
    - `name`: The name of the valve.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)

    async def _update(self) -> None:
        logger.trace(f"Current temperature for {self.name} is {self.temp}")
