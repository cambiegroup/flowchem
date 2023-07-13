"""FastAPI server for devices control."""
from typing import Iterable

from fastapi import FastAPI, APIRouter
from importlib.metadata import metadata, version

from loguru import logger
from starlette.responses import RedirectResponse

from flowchem.components.device_info import DeviceInfo

# from fastapi_utils.tasks import repeat_every

from flowchem.vendor.repeat_every import repeat_every
from flowchem.devices.flowchem_device import RepeatedTaskInfo


class FastAPIServer:
    def __init__(self, filename: str = ""):
        # Create FastAPI app
        self.app = FastAPI(
            title=f"Flowchem - {filename}",
            description=metadata("flowchem")["Summary"],
            version=version("flowchem"),
            license_info={
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            },
        )

        self._add_root_redirect()

    def _add_root_redirect(self):
        @self.app.route("/")
        def home_redirect_to_docs(root_path):
            """Redirect root to `/docs` to enable interaction w/ API."""
            return RedirectResponse(url="/docs")

    def add_background_tasks(self, repeated_tasks: Iterable[RepeatedTaskInfo]):
        """Schedule repeated tasks to run upon server startup."""
        for seconds_delay, task in repeated_tasks:

            @self.app.on_event("startup")
            @repeat_every(seconds=seconds_delay)
            async def my_task():
                logger.debug("Running repeated task...")
                await task()

    def add_device(self, device):
        """Add device to server"""
        # Get components (some compounded devices can return multiple components)
        components = device.components()
        logger.debug(f"Got {len(components)} components from {device.name}")

        # Base device endpoint
        device_root = APIRouter(prefix=f"/{device.name}", tags=[device.name])
        device_root.add_api_route(
            "/",
            device.get_device_info,  # TODO: add components in the device info response!
            methods=["GET"],
            response_model=DeviceInfo,
        )
        self.app.include_router(device_root)

        # Add repeated tasks for device if any
        if tasks := device.repeated_task():
            self.add_background_tasks(tasks)

        # add device components
        for component in components:
            self.app.include_router(component.router, tags=component.router.tags)
            logger.debug(f"Router <{component.router.prefix}> added to app!")
