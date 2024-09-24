from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Query

from flowchem.components.analytics.ms import MSControl

if TYPE_CHECKING:
    from flowchem.devices import WatersMS


class WatersMSControl(MSControl):
    hw_device: WatersMS  # for typing's sake

    def __init__(self, name: str, hw_device: WatersMS) -> None:
        """Device-specific initialization."""
        super().__init__(name, hw_device)

    async def run_sample(self, sample_name: str) -> bool:
        ...
