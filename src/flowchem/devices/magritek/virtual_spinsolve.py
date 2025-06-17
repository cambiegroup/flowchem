from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.magritek.spinsolve_control import SpinsolveControl
from flowchem.utils.people import samuel_saraiva
from fastapi import BackgroundTasks


class VirtualSpinsolve(FlowchemDevice):

    def __init__(self, name: str | None = None, **kwargs) -> None:
        """Control a Spinsolve instance via HTTP XML API."""
        super().__init__(name)
        self.device_info.version = "Virtual Spinsolve"
        self.device_info.model = "Virtual Spectrometer"
        self.device_info.authors = [samuel_saraiva]

    async def initialize(self):
        self.components.append(SpinsolveControl("nmr-control", self)) # type: ignore

    async def get_sample(self) -> str:
        return ""

    async def set_sample(self, sample: str):
        return ""

    async def get_solvent(self) -> str:
        return ""

    async def set_solvent(self, solvent: str):
        return ""

    async def get_user_data(self) -> dict:
        return {}

    async def set_user_data(self, data: dict):
        return {}

    async def list_protocols(self):
        return []

    async def get_result_folder(self, result_id: int | None = None):
        return ""

    async def is_protocol_running(self) -> bool:
        return True


    async def run_protocol(
        self,
        name,
        background_tasks: BackgroundTasks,
        options=None,
    ) -> int:
        return 1

    async def abort(self):
        ...