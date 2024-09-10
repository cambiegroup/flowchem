from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from types import FunctionType
import inspect

from fastapi import APIRouter
from loguru import logger

from flowchem.components.component_info import ComponentInfo

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class FlowchemComponent:
    """
    A base class for Flowchem components that integrates with a hardware device.

    This class provides the foundational setup for creating components that can
    communicate with hardware devices and expose API routes for interacting with these components.

    Attributes:
    -----------
    name : str
        The name of the component.
    hw_device : FlowchemDevice
        The hardware device instance associated with this component.
    component_info : ComponentInfo
        Metadata about the component.
    _router : APIRouter
        The API router for the component to define HTTP endpoints.

    Methods:
    --------
    add_api_route(path: str, endpoint: Callable, **kwargs):
        Add an API route to the component's router.
    get_component_info() -> ComponentInfo:
        Retrieve the component's metadata.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice, api_parent_method=False) -> None:
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

        # Include the parent methods in the API server, including methods that were not overwritten.
        self.include_parent_method = api_parent_method

        self.insertAPI_automatically()

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

    def insertAPI_automatically(self):
        """
        Automatically insert API routes for the component's methods.

        This method scans the component and its parent classes for methods that can be exposed as API routes.
        It includes methods from the parent classes if `include_parent_method` is set to True. If a method is not
        overwritten, a warning is added to its documentation to inform the user about potential challenges when
        transitioning to different hardware.

        Methods with no arguments are exposed as GET routes, while methods with arguments are exposed as PUT routes.
        """

        api_class_methods = [x for x, y in self.__class__.__dict__.items() if
                             type(y) == FunctionType and y.__name__ != "__init__"]

        obj_methods = []
        for p in self.__class__.__mro__:
            classname = p.__name__
            if classname != self.__class__.__name__ and classname != "FlowchemComponent":
                obj_methods = obj_methods + [x for x, y in p.__dict__.items() if
                                             type(y) == FunctionType and y.__name__ != "__init__"]

        # check and insert
        for api_method in api_class_methods + obj_methods:
            if (api_method in obj_methods) and (api_method not in api_class_methods) and not self.include_parent_method:
                # This means that the method was not overwritten and belong only to the parent class, however the user
                # does not want to include it in the API
                continue

            if (api_method in api_class_methods) and (api_method not in obj_methods):
                # This means that the method was not overwritten
                # The documentation must be changed to clarify it to the user
                msg = (
                    f"This method/function is tailored specifically for the {api_method}. If you choose to use it in your "
                    "automation, transitioning to a different device from another supplier may become more "
                    "challenging.")
                self.__class__.__dict__[api_method].__doc__ += f"\n\nWarning:\n{msg}"

            # do insertion here
            method = getattr(self, api_method)
            argumentsdesc = inspect.getfullargspec(method)
            argsnum = len(argumentsdesc.args)

            bound_method = method.__get__(self)

            if argsnum == 1:
                self.add_api_route(f"/{api_method}", bound_method, methods=["GET"])
            else:
                self.add_api_route(f"/{api_method}", bound_method, methods=["PUT"])



