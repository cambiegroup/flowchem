from __future__ import annotations
import asyncio
import time
from typing import Optional, AsyncGenerator, TYPE_CHECKING
from warnings import warn

from loguru import logger

from flowchem.units import flowchem_ureg
from flowchem.components.stdlib import ActiveComponent

if TYPE_CHECKING:
    from flowchem import Experiment


class Sensor(ActiveComponent):
    """
    A generic sensor.

    Attributes:
    - `name`: The name of the Sensor.
    - `rate`: Data collection rate in Hz as a `pint.Quantity`. A rate of 0 Hz corresponds to the sensor being off.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.rate = flowchem_ureg.parse_expression("0 Hz")
        self._visualization_shape = "ellipse"
        self._unit: str = ""
        self._base_state = {"rate": "0 Hz"}

    async def _read(self):
        """
        Collects the data.
        In the generic `Sensor` implementation, this raises a `NotImplementedError`.
        Subclasses of `Sensor` should implement their own version of this method.
        """
        raise NotImplementedError

    async def _monitor(
        self, experiment: "Experiment", dry_run: bool = False
    ) -> AsyncGenerator:
        """
        If data collection is off and needs to be turned on, turn it on.
        If data collection is on and needs to be turned off, turn off and return data.
        """
        while not experiment._end_loop:  # type: ignore
            # if the sensor is off, hand control back over
            if not self.rate:
                await asyncio.sleep(0)
                continue

            if not dry_run:
                yield {"data": await self._read(), "timestamp": time.time()}
            else:
                yield {"data": "simulated read", "timestamp": time.time()}

            # then wait for the sensor's next read
            if self.rate:
                await asyncio.sleep(1 / self.rate.m_as("Hz"))

        logger.debug(f"Monitor loop for {self} has completed.")

    async def _validate_read(self):
        async with self:
            logger.trace("Context entered")
            res = await self._read()
            if not res:
                warn(
                    "Sensor reads should probably return data. "
                    f"Currently, {self}._read() does not return anything."
                )

    def _validate(self, dry_run: bool) -> None:
        logger.debug(f"Performing sensor specific checks for {self}...")
        if not dry_run:
            logger.trace("Executing Sensor-specific checks...")
            logger.trace("Entering context...")
            asyncio.run(self._validate_read())
        logger.trace("Performing general component checks...")
        super()._validate(dry_run=dry_run)

    async def _update(self) -> None:
        # sensors don't have an update method; they implement read
        pass
