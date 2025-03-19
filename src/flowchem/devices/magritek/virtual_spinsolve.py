from fastapi import BackgroundTasks

from .spinsolve import Spinsolve, SpinsolveControl
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import asyncio
import pint


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