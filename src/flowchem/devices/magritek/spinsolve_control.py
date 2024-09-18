from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import BackgroundTasks

from flowchem.components.analytics.nmr import NMRControl

if TYPE_CHECKING:
    from .spinsolve import Spinsolve


class SpinsolveControl(NMRControl):
    hw_device: Spinsolve  # for typing's sake

    def __init__(self, name: str, hw_device: Spinsolve) -> None:  # type:ignore
        """HPLC Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        # Solvent
        #self.add_api_route("/solvent", self.get_solvent, methods=["GET"])
        #self.add_api_route("/solvent", self.set_solvent, methods=["PUT"])
        # Sample name
        #self.add_api_route("/sample-name", self.get_sample, methods=["GET"])
        #self.add_api_route("/sample-name", self.set_sample, methods=["PUT"])
        # User data
        #self.add_api_route("/user-data", self.get_user_data, methods=["GET"])
        #self.add_api_route("/user-data", self.set_user_data, methods=["PUT"])
        # Protocols
        #self.add_api_route(
        #    "/protocol-list",
        #    self.list_protocols,
        #    methods=["GET"],
        #)
        #self.add_api_route(
        #    "/spectrum-folder",
        #    self.get_result_folder,
        #    methods=["GET"],
        #)
        #self.add_api_route(
        #    "/is-busy",
        #    self.is_protocol_running,
        #    methods=["GET"],
        #)

    async def acquire_spectrum(
        self,
        background_tasks: BackgroundTasks,
        protocol="H",
        options=None,
    ) -> int:
        """Acquire an NMR spectrum.

        Return an ID to be passed to get_result_folder, it will return the result folder after acquisition end.
        """
        return await self.hw_device.run_protocol(
            name=protocol,
            background_tasks=background_tasks,
            options=options,
        )

    async def stop(self):
        return await self.hw_device.abort()

    # Solvent
    async def get_solvent(self) -> str:
        """Get current solvent."""
        reply = await self.hw_device.get_solvent()
        return reply

    async def set_solvent(self, solvent: str):
        """Set solvent."""
        await self.hw_device.set_solvent(solvent)

    # Sample name
    async def get_sample(self) -> str:
        """Get current sample."""
        reply = await self.hw_device.get_sample()
        return reply

    async def set_sample(self, sample: str):
        """Set the sample name (it will appear in `acqu.par`)."""
        await self.hw_device.set_sample(sample)

    # User data
    async def get_user_data(self) -> dict:
        """Get user data. These will appear in `acqu.par`."""
        reply = await self.hw_device.get_user_data()
        return reply

    async def set_user_data(self, data: dict):
        """Set user data. The items provide will appear in `acqu.par`."""
        await self.hw_device.set_user_data(data)

    # Protocols
    def list_protocols(self) -> list[str]:
        """Return known protocol names."""
        reply = self.hw_device.list_protocols()
        return reply

    async def get_result_folder(self, result_id: int | None = None) -> str:
        """Get the result folder with the given ID or the last one if no ID is specified. Empty str if not existing."""
        # If no result_id get last
        reply = await self.hw_device.get_result_folder(result_id)
        return reply

    async def is_protocol_running(self) -> bool:
        """Return True if a protocol is running, otherwise False."""
        reply = await self.hw_device.is_protocol_running()
        return reply



