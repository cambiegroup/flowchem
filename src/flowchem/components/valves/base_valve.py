"""Generic valve."""
from __future__ import annotations

from pydantic import BaseModel

from flowchem.components.base_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class ValveInfo(BaseModel):
    ports: list[str]
    positions: dict[str, list[tuple[str, str]]]


class BaseValve(FlowchemComponent):
    """An abstract class for devices of type valve.

    .. warning::
        Device objects should not directly generate components with this object but rather a more specific valve type,
        such as `InjectionValve` or `MultiPositionValve`.

    All valves are characterized by:

    - a `positions` attribute, which is a set of strings representing the valve positions.
    - a `set_position()` method
    - a `get_position()` method
    """

    def __init__(
        self,
        name: str,
        hw_device: FlowchemDevice,
        positions: dict[str, list[tuple[str, str]]],
        ports: list[str],
    ) -> None:
        """Create a valve object.

        Args:
        ----
            name: device name, passed to FlowchemComponent.
            hw_device: the object that controls the hardware.
            positions: list of string representing the valve ports. The order in the list reflect the physical world.
                       This potentially enables to select rotation direction to avoid specific interactions.
        """
        assert len(set(positions)) == len(positions), "Positions are unique"
        self._positions = positions
        self._ports = ports  # This is necessary because the port order cannot be determined from ValvePosition only

        super().__init__(name, hw_device)

        self.add_api_route("/position", self.get_position, methods=["GET"])
        self.add_api_route("/position", self.set_position, methods=["PUT"])
        self.add_api_route("/connections", self.connections, methods=["GET"])

    async def get_position(self) -> str:  # type: ignore
        """Get the current position of the valve."""
        ...

    async def set_position(self, position: str) -> bool:
        """Set the valve to the specified position."""
        assert position in self._positions
        return True

    def connections(self) -> ValveInfo:
        """Get the list of all available positions for this valve.

        These are the human-friendly port names, and they do not necessarily match the port names used in the
        communication with the device.
        E.g. positions "load" and "inject" could translate to positions "1" and "2".
        """
        return ValveInfo(ports=self._ports, positions=self._positions)
