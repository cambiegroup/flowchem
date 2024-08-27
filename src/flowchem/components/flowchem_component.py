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

    def insertAPI_automatically(self, api_class, obj, include_parent_method=False):
        """
        Automatically insert API routes into the possibles_component's router based on methods in an API class.

        This method adds routes for methods defined in `api_class` that are not overridden
        in the instance `obj`. It also updates the documentation of these methods to reflect
        potential challenges in switching to a different device supplier.

        Parameters:
        -----------
        api_class : type
            The class containing methods that should be exposed as API routes. These methods
            should be defined in the class and not be `__init__`.
        obj : object
            The instance of the class being checked for method overrides. This instance's
            method resolution order (MRO) is inspected to determine if the methods from
            `api_class` are overridden.

        Notes:
        ------
        - Methods from `api_class` that are not present in `obj`'s MRO are considered as
          not overridden and are added to the API router.
        - The inserted routes will use GET or PUT methods based on the number of arguments
          required by the API methods.

        Example:
        --------
        If `api_class` defines a method `do_something`, and `obj` does not override this method,
        a route will be added to the possibles_component's API router to handle requests to `/do_something`.
        """

        api_class_methods = [x for x, y in api_class.__dict__.items() if
                             type(y) == FunctionType and y.__name__ != "__init__"]

        obj_methods = []
        for p in obj.__class__.__mro__:
            classname = p.__name__
            if classname != api_class.__name__ and classname != "FlowchemComponent":
                obj_methods = obj_methods + [x for x, y in p.__dict__.items() if
                                             type(y) == FunctionType and y.__name__ != "__init__"]

        # check and insert
        for api_method in api_class_methods + obj_methods:
            if (api_method in obj_methods) and (api_method not in api_class_methods) and not include_parent_method:
                # This means that the method was not overwritten and belong only to the parent class, however the user
                # does not want to nclude it in the API
                continue

            if (api_method in api_class_methods) and (api_method not in obj_methods):
                # This means that the method was not overwritten
                # The documentation must be changed to clarify it to the user
                msg = (
                    f"This method/function is tailored specifically for the {api_method}. If you choose to use it in your "
                    "automation, transitioning to a different device from another supplier may become more "
                    "challenging.")
                api_class.__dict__[api_method].__doc__ += f"\n\nWarning:\n{msg}"

            # do insertion here
            method = getattr(obj, api_method)
            argumentsdesc = inspect.getfullargspec(method)
            argsnum = len(argumentsdesc.args)

            bound_method = method.__get__(obj)

            if argsnum == 1:
                self.add_api_route(f"/{api_method}", bound_method, methods=["GET"])
            else:
                self.add_api_route(f"/{api_method}", bound_method, methods=["PUT"])



