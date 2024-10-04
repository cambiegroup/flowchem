from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Callable
from functools import wraps
import os

from fastapi import APIRouter
from loguru import logger

from flowchem.components.component_info import ComponentInfo
import flowchem.client as logging_dir

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


# Define a decorator that logs without altering the endpoint's function signature
def log_usage(func: Callable, component: str):
    @wraps(func)  # This ensures FastAPI can introspect the function correctly
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        msg = f"Endpoint {func.__name__.split(".")[-1]}"
        logger.bind(module=component).info(f"{msg} called with (args): {args}, kwargs: {kwargs}")
        logger.bind(module=component).info(f"{msg} returned: {result}")
        return result
    return wrapper


class FlowchemComponent:
    """
    A base class for Flowchem components that integrates with a hardware device and provides an API interface.

    This class enables the creation of components that interact with hardware devices in Flowchem and
    expose API routes for interacting with these components via HTTP. It also includes automatic logging
    for all defined API routes.

    Attributes:
    -----------
    name : str
        The name of the component.
    hw_device : FlowchemDevice
        The hardware device instance associated with this component.
    component_info : ComponentInfo
        Metadata about the component, including name and parent device information.
    _router : APIRouter
        The API router used to define and manage HTTP endpoints for the component.

    Methods:
    --------
    __init_subclass__(cls, **kwargs):
        Automatically wraps all methods of the subclass with the `log_usage` decorator, except for `__init__`.
    __init__(self, name: str, hw_device: FlowchemDevice):
        Initializes the component with its name and hardware device, and sets up the API router.
    creating_logger_sink(self):
        Sets up the log file for the component, based on the hardware device name and class name, and ensures
        logging is filtered to include only records from the current component's module.
    router(self) -> APIRouter:
        Returns the API router instance for the component, which can be extended with additional routes.
    add_api_route(self, path: str, endpoint: Callable, **kwargs):
        Adds an API route to the component's router, logging each route addition and storing the associated
        method in the component metadata for PUT and GET routes.
    get_component_info(self) -> ComponentInfo:
        Provides metadata about the component, such as its name and associated hardware device, as a response
        to an HTTP GET request.
    """
    def __init_subclass__(cls, **kwargs):
        """
        Automatically invoked when a subclass is created.

        This method wraps all callable attributes (except `__init__`) of the subclass with the `log_usage`
        decorator, which logs information about the function call and its result. This ensures that all
        API endpoints in the subclass automatically log their usage without modifying their function signatures.

        Parameters:
        -----------
        cls : type
            The subclass being created.
        kwargs : dict
            Additional arguments passed to the subclass initialization.
        """
        super().__init_subclass__(**kwargs)
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and attr_name != "__init__":
                setattr(cls, attr_name, log_usage(attr_value, cls.__name__))

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Initialize the FlowchemComponent with a name and associated hardware device.

        Parameters:
        -----------
        name : str
            The name assigned to this component.
        hw_device : FlowchemDevice
            The hardware device instance associated with this component.
        """
        self.name = name
        self.hw_device = hw_device
        self.component_info = ComponentInfo(
            name=name,
            parent_device=self.hw_device.name,
            inheritance=[f"{parent.__module__}.{parent.__name__}" for parent in self.__class__.mro()]
        )

        # Initialize router
        self._router = APIRouter(
            prefix=f"/{self.component_info.parent_device}/{name}",
            tags=[self.component_info.parent_device],
        )
        self.add_api_route(
            "/",
            self.get_component_info,
            methods=["GET"],
            response_model=ComponentInfo,
        )

        self.creating_logger_sink()

    def creating_logger_sink(self):
        """
        Set up a dedicated log file for the component's logging.

        This method creates a log file specific to the current component based on its hardware device name and class name.
        It ensures that logs are filtered so that only records related to the current component's module are written to the log.

        Steps:
        ------
        1. Creates a subdirectory for the hardware device if it doesn't exist.
        2. If a log file for the component already exists, it is removed to clear any previous logs.
        3. Adds a log sink with a filter to capture only log entries relevant to the current component.

        The log file is named as `<class_name>.log` and placed under `loggings/<hardware_device_name>/`.

        Returns:
        --------
        None
        """
        log_directory = os.path.join(os.path.dirname(logging_dir.__file__),"loggings")
        sink_address = f"{log_directory}/{self.hw_device.name}"
        sink_name = self.__class__.__name__

        if os.path.exists(sink_address):
            # Clear the memory
            os.remove(f"{sink_address}/{sink_name}.log")
        else:
            # Creating the news sink
            os.mkdir(sink_address)

        logger.add(f"{sink_address}/{sink_name}.log",
                   filter=lambda record: record["extra"].get("module") == f"{sink_name}",
                   format="{time}-{message}")

    @property
    def router(self):
        """
        Return the API router.

        This serves as a hook for subclasses to add their specific routes.

        Returns:
        --------
        APIRouter
            The API router instance.
        """
        return self._router

    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """
        Add an API route to the component's router.

        This method allows subclasses to define their own API endpoints.

        Parameters:
        -----------
        path : str
            The URL path for the API route.
        endpoint : Callable
            The function to be called when the route is accessed.
        kwargs : dict
            Additional arguments to configure the route.
        """
        if kwargs["methods"][0] == "PUT":
            self.component_info.put_methods[path[1:]] = endpoint.__name__
        if kwargs["methods"][0] == "GET" and path != "/":
            self.component_info.get_methods[path[1:]] = endpoint.__name__

        logger.debug(f"Adding route {path} for router of {self.name}")

        self._router.add_api_route(path, endpoint, **kwargs)

    def get_component_info(self) -> ComponentInfo:
        """
        Retrieve the component's metadata.

        This endpoint provides information about the component, such as its name and associated hardware device.

        Returns:
        --------
        ComponentInfo
            Metadata about the component.
        """
        return self.component_info

