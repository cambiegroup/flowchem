"""Knauer valve component."""
from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .knauer_valve import KnauerValve
from flowchem.components.valves.distribution_valves import (
    SixPortDistributionValve,
    SixteenPortDistributionValve,
    TwelvePortDistributionValve,
)
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve


class KnauerInjectionValve(SixPortTwoPositionValve):
    """
    Control a Knauer Injection Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """
    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the KnauerInjectionValve component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerValve): The hardware device instance for controlling the Knauer valve.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    class LoadInject(Enum):
        LOAD = "L"
        INJECT = "I"

    def _change_connections(self, raw_position: str | int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (str | int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            str | int: The mapped position.
        """
        position_mapping = {0: "L", 1: "I"}
        if reverse:
            return str([key for key, value in position_mapping.items() if value == raw_position][0])
        else:
            return position_mapping[raw_position]

    async def get_monitor_position(self) -> str:
        """
        Get the current valve position.

        Returns:
            str: The current position (LOAD or INJECT).
        """
        pos = self.LoadInject(await self.hw_device.get_raw_position())
        return pos.name

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position (LOAD or INJECT).

        Returns:
            str: The response from the hardware device.
        """
        try:
            return await self.hw_device.set_raw_position(self.LoadInject[position.upper()].value)
        except KeyError as e:
            raise Exception(f"Please give allowed positions {[pos.name for pos in self.LoadInject]}") from e


class Knauer6PortDistributionValve(SixPortDistributionValve):
    """
    Control a Knauer 6-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the Knauer6PortDistributionValve component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerValve): The hardware device instance for controlling the Knauer valve.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        """
        Get the current valve position.

        Returns:
            str: The current position.
        """
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.set_raw_position(position)


class Knauer12PortDistributionValve(TwelvePortDistributionValve):
    """
    Control a Knauer 12-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the Knauer12PortDistributionValve component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerValve): The hardware device instance for controlling the Knauer valve.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        """
        Get the current valve position.

        Returns:
            str: The current position.
        """
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.set_raw_position(position)


class Knauer16PortDistributionValve(SixteenPortDistributionValve):
    """
    Control a Knauer 16-Port Distribution Valve.

    Attributes:
        hw_device (KnauerValve): The hardware device for the Knauer valve.
    """

    hw_device: KnauerValve  # for typing's sake

    def __init__(self, name: str, hw_device: KnauerValve) -> None:
        """
        Initialize the Knauer16PortDistributionValve component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerValve): The hardware device instance for controlling the Knauer valve.
        """
        super().__init__(name, hw_device)

        self.add_api_route("/monitor_position", self.get_monitor_position, methods=["GET"])
        self.add_api_route("/monitor_position", self.set_monitor_position, methods=["PUT"])

    def _change_connections(self, raw_position: int, reverse: bool = False):
        """
        Change connections based on the valve's raw position.

        Args:
            raw_position (int): The raw position of the valve.
            reverse (bool): Whether to reverse the mapping.

        Returns:
            int: The mapped position.
        """
        if reverse:
            return raw_position - 1
        else:
            return raw_position + 1

    async def get_monitor_position(self) -> str:
        """
        Get the current valve position.

        Returns:
            str: The current position.
        """
        return await self.hw_device.get_raw_position()

    async def set_monitor_position(self, position: str):
        """
        Set the valve to a specified position.

        Args:
            position (str): The desired position.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.set_raw_position(position)
