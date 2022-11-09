"""Knauer valve component."""
from ...components.valves.distribution_valves import SixPortDistribution
from ...components.valves.distribution_valves import SixteenPortDistribution
from ...components.valves.distribution_valves import TwelvePortDistribution
from ...components.valves.injection_valves import SixPortTwoPosition
from .valve import KnauerValve


class KnauerInjectionValve(SixPortTwoPosition):
    hw_device: KnauerValve  # for typing's sake
    position_mapping = {"load": "L", "inject": "I"}
    _reverse_position_mapping = {v: k for k, v in position_mapping.items()}

    async def get_position(self) -> str:
        pos = await self.hw_device.get_raw_position()
        assert pos in ("L", "I"), "Valve position is 'I' or 'L'"
        return self._reverse_position_mapping[pos]

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        target_pos = KnauerInjectionValve.position_mapping[position]
        return await self.hw_device.set_raw_position(target_pos)


class Knauer6PortDistribution(SixPortDistribution):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Return current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)


class Knauer12PortDistribution(TwelvePortDistribution):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Return current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)


class Knauer16PortDistribution(SixteenPortDistribution):
    """KnauerValve of type SIX_PORT_SIX_POSITION."""

    hw_device: KnauerValve  # for typing's sake

    async def get_position(self) -> str:
        """Return current valve position."""
        return await self.hw_device.get_raw_position()

    async def set_position(self, position: str):
        """Move valve to position."""
        await super().set_position(position)
        return await self.hw_device.set_raw_position(position)
