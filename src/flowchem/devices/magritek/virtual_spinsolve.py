from .spinsolve import Spinsolve, SpinsolveControl
from fastapi import BackgroundTasks


class VirtualSpinsolve(Spinsolve):

    async def initialize(self):

        self.components.append(SpinsolveControl("nmr-control", self))

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

    async def run_protocol(
        self,
        name,
        background_tasks: BackgroundTasks,
        options=None,
    ) -> int:
        return 1

    async def abort(self):
        ...