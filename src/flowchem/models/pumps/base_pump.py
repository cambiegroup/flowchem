"""Base pump."""
from abc import ABC

from fastapi import APIRouter

from flowchem.models.base_device import BaseDevice


class BasePump(BaseDevice, ABC):
    """A generic pumping device."""

    def __init__(self, name: str | None = None):
        """Add ontology class and call superclass constructor."""
        super().__init__(name=name)
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0001042")

    async def set_flow_rate(self, rate: str):
        """Set pump infusion flow rate."""
        raise NotImplementedError

    async def get_flow_rate(self) -> float:
        """Get pump infusion flow rate."""
        raise NotImplementedError

    async def infuse(self):
        """Start infusion."""
        raise NotImplementedError

    async def stop(self):
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
    """
    This mixin represent the capability of a pump to invert the flow direction.

    Most of the methods are mutuated from BasePump.
    Note that withdraw as it is defined here applies both to peristaltic and syringe pumps.
    """

    def withdraw(self):
        """Pump in the opposite direction of infuse."""
        raise NotADirectoryError

    async def set_withdrawing_flow_rate(self, rate: str):
        """Set pump withdraw flow rate."""
        raise NotImplementedError

    async def get_withdrawing_flow_rate(self) -> float:
        """Get pump withdraw flow rate."""
        raise NotImplementedError

    def get_router(self, prefix: str | None = None) -> APIRouter:
        """Get the API router for this device."""
        router = super().get_router(prefix)  # type: ignore

        router.add_api_route(
            "/withdraw-flow-rate", self.get_withdrawing_flow_rate, methods=["GET"]
        )
        router.add_api_route(
            "/withdraw-flow-rate", self.set_withdrawing_flow_rate, methods=["PUT"]
        )
        router.add_api_route("/withdraw", self.withdraw, methods=["PUT"])

        return router
