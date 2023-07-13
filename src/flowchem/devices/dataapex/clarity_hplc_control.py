from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Query

from flowchem.components.analytics.hplc import HPLCControl

if TYPE_CHECKING:
    from flowchem.devices import Clarity


class ClarityComponent(HPLCControl):
    hw_device: Clarity  # for typing's sake

    def __init__(self, name: str, hw_device: Clarity) -> None:
        """Device-specific initialization."""
        super().__init__(name, hw_device)
        # Clarity-specific command
        self.add_api_route("/exit", self.exit, methods=["PUT"])

    async def exit(self) -> bool:
        """Exit Clarity Chrom."""
        return await self.hw_device.execute_command("exit", without_instrument_num=True)

    async def send_method(
        self,
        method_name: str = Query(
            default=...,
            description="Name of the method file",
            examples=["MyMethod.MET"],
            alias="method-name",
        ),
    ) -> bool:
        """Sets the HPLC method (i.e. a file with .MET extension) to the instrument.

        Make sure to select 'Send Method to Instrument' option in Method Sending Options dialog in System Configuration.
        """
        return await self.hw_device.execute_command(f" {method_name}")

    async def run_sample(
        self,
        sample_name: str = Query(
            default=...,
            description="Sample name",
            examples=["JB-123-crude-2h"],
            alias="sample-name",
        ),
        method_name: str = Query(
            default=...,
            description="Name of the method file",
            examples=["MyMethod.MET"],
            alias="method-name",
        ),
    ) -> bool:
        """Run one analysis on the instrument.

        Note that it takes at least 2 sec until the run actually starts (depending on instrument configuration).
        While the export of the chromatogram in e.g. ASCII format can be achieved programmatically via the CLI, the best
        solution is to enable automatic data export for all runs of the HPLC as the chromatogram will be automatically
        exported as soon as the run is finished.
        """
        if not await self.hw_device.execute_command(f'set_sample_name="{sample_name}"'):
            return False
        if not await self.send_method(method_name):
            return False
        return await self.hw_device.execute_command(
            f"run={self.hw_device.instrument}",
            without_instrument_num=True,
        )
