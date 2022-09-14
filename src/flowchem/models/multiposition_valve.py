"""Generic multiposition valve."""
from __future__ import annotations

from abc import ABC

from .base_valve import BaseValve


class MultipositionValve(BaseValve, ABC):
    """An abstract class for devices of type multiposition valve."""

    _DEFAULT_POSITION = "1"

    def __init__(self, port_count: int = 16, default_position: int = 1, name=None):
        """

        Args:
            port_count (int): number of available positions, automatically create port names based on this.
            default_position (int): the port number to be set upon initialization.
            name (str): device name, passed to BaseDevice.
        """
        super().__init__(
            positions={str(x + 1) for x in range(port_count)},
            default_position=str(default_position),
            name=name,
        )
        # e.g. port_count=6
        # {'1', '2', '3', '4', '5', '6'}
        # e.g. port_count=12
        # {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
