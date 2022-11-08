"""Base pump component."""
from abc import ABC

from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class BasePump(FlowchemComponent, ABC):
    def __int__(self, name: str, hw_device: FlowchemDevice):
        """A generic pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/infuse", self.infuse, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/is-pumping", self.is_pumping, methods=["GET"])
        if self.is_withdrawing_capable():
            self.add_api_route("/withdraw", self.withdraw, methods=["PUT"])

    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        """Start infusion."""
        ...

    async def stop(self) -> bool:
        """Stop pumping."""
        ...

    async def is_pumping(self) -> bool:
        """Is pump running?"""
        ...

    @staticmethod
    def is_withdrawing_capable() -> bool:
        """Can the pump reverse its normal flow direction?"""
        ...

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:
        """Pump in the opposite direction of infuse."""
        ...
