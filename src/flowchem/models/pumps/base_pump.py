from abc import ABC

from fastapi import APIRouter
from flowchem.models.base_device import BaseDevice
from flowchem.units import flowchem_ureg


class BasePump(BaseDevice, ABC):
    """
    A generic pumping device whose primary feature is that it moves fluid.

    Arguments:
    - `name`: The name of the pump.

    Attributes:
    - `name`: The name of the pump.
    - `rate`: The flow rate of the pump as a `pint.Quantity`. Must be of the dimensionality of volume/time.
    """

    def __init__(self, name: str | None = None):
        super().__init__(name=name)
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0001042")

    def set_flow_rate(self, rate: str):
        """Sets the pump infusion flow rate."""
        raise NotImplementedError

    def get_flow_rate(self) -> float:
        """Gets the pump infusion flow rate."""
        raise NotImplementedError

    def infuse(self):
        """Start infusion."""
        raise NotImplementedError

    def stop(self):
        """Stop pumping."""
        raise NotImplementedError

    def get_router(self, prefix: str | None = None) -> APIRouter:
        """Get the API router for this device."""
        router = BaseDevice.get_router(self, prefix)

        router.add_api_route("/flow-rate", self.get_flow_rate, methods=["GET"])
        router.add_api_route("/flow-rate", self.set_flow_rate, methods=["PUT"])
        router.add_api_route("/infuse", self.infuse, methods=["PUT"])
        router.add_api_route("/stop", self.stop, methods=["PUT"])

        return router


class WithdrawMixin:
    def withdraw(self):
        """Pump in the opposite direction of infuse."""
        raise NotADirectoryError

    def set_withdrawing_flow_rate(self, rate: str):
        """Sets the pump withdraw flow rate."""
        raise NotImplementedError

    def get_withdrawing_flow_rate(self) -> float:
        """Gets the pump withdraw flow rate."""
        raise NotImplementedError

    def get_router(self, prefix: str | None = None) -> APIRouter:
        """Get the API router for this device."""
        router = super().get_router(prefix)

        router.add_api_route(
            "/withdraw-flow-rate", self.get_withdrawing_flow_rate, methods=["GET"]
        )
        router.add_api_route(
            "/withdraw-flow-rate", self.set_withdrawing_flow_rate, methods=["PUT"]
        )
        router.add_api_route("/withdraw", self.withdraw, methods=["PUT"])

        return router
