"""Generic multiposition valve."""
from __future__ import annotations

from abc import ABC

from .base_valve import BaseValve


class MultipositionValve(BaseValve, ABC):
    """A generic multi-position valve."""

    _DEFAULT_POSITION = "1"

    def __init__(self, positions: int = 16, **kwargs):
        """
        Initialize a generic multi-position valve.

        Args:
            positions: in with the number of available positions
        """
        super().__init__(**kwargs)

        self.positions = {str(x + 1) for x in range(positions)}
        # e.g. position=6
        # positions = {'1', '2', '3', '4', '5', '6'}
        # e.g. position=12
        # {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
