"""Base pump component."""
from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class BasePump(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice):
        """A generic pump."""
        super().__init__(name, hw_device)
        self.add_api_route("/infuse", self.infuse, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])
        self.add_api_route("/is-pumping", self.is_pumping, methods=["GET"])
        if self.is_withdrawing_capable():
            self.add_api_route("/withdraw", self.withdraw, methods=["PUT"])

    async def infuse(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Start infusion."""
        ...

    async def stop(self):  # type: ignore
        """Stop pumping."""
        ...

    async def is_pumping(self) -> bool:  # type: ignore
        """Is pump running?"""
        ...

    @staticmethod
    def is_withdrawing_capable() -> bool:  # type: ignore
        """Can the pump reverse its normal flow direction?"""
        ...

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:  # type: ignore
        """Pump in the opposite direction of infuse."""
        ...
