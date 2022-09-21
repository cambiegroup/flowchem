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
        self.rate = flowchem_ureg.parse_expression("0 ml/min")
        self.owl_subclass_of.add("http://purl.obolibrary.org/obo/OBI_0001042")

    def set_flow_rate(self, rate: str):
        """Sets the pump flow rate. In case of infusion/withdraw syringe pumps, sets infusion rate."""
        self.rate = flowchem_ureg.parse_expression(rate)

    def get_flow_rate(self) -> float:
        """Gets the pump flow rate in the current moving direction. If not moving, default to infusion rate."""
        return self.rate.m_as("ml/min")

    def infuse(self):
        """Start infusion."""
        raise NotImplementedError

    def stop(self):
        """Stop pumping."""
        raise NotImplementedError

    def get_router(self) -> APIRouter:
        """Get the API router for this device."""
        router = BaseDevice.get_router(self)

        router.add_api_route("/flow-rate", self.get_flow_rate, methods=["GET"])
        router.add_api_route("/flow-rate", self.set_flow_rate, methods=["PUT"])
        router.add_api_route("/infuse", self.infuse, methods=["PUT"])
        router.add_api_route("/stop", self.stop, methods=["PUT"])

        if hasattr(self, "withdraw"):
            router.add_api_route("/withdraw", self.withdraw, methods=["PUT"])  # type: ignore

        return router


class WithdrawMixin:
    def withdraw(self):
        """Pump in the opposite direction of infuse."""
        raise NotADirectoryError
