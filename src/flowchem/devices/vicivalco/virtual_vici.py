from .vici_valve import ViciValve, ViciValcoValveIO, ViciInjectionValve


class VirtualIO(ViciValcoValveIO):

    def __init__(self):
        ...


class VirtualViciValve(ViciValve):

    @classmethod
    def from_config(
        cls,
        port: str,
        address: int,
        name: str = "",
        **serial_kwargs,
    ):
        asw = cls(VirtualIO(), address=address, name=name)
        asw.device_info.version = "Virtual"
        asw._position = "1"
        return asw

    async def initialize(self):
        # Add component
        self.components.append(ViciInjectionValve("injection-valve", self))

    async def set_raw_position(self, position: str):
        self._position = position

    async def get_raw_position(self) -> str:
        return self._position




