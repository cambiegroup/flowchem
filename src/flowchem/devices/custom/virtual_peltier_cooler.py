from .peltier_cooler import PeltierCooler, PeltierIO, PeltierCommand
from loguru import logger


class VirtualPeltierIO(PeltierIO):
    ...

    @classmethod
    def from_config(cls, port, **serial_kwargs):
        return cls(port)

    async def _write(self, command: PeltierCommand):
        command_compiled = command.compile()
        logger.debug(f"Sending virtual command: {repr(command_compiled)}")

    async def _read_reply(self, command) -> str:
        reply_string = ""
        logger.debug(f"Reply fake received: ")
        return reply_string


class VirtualPeltierCooler(PeltierCooler):

    @classmethod
    def from_config(
            cls,
            port: str,
            address: int,
            name: str = "",
            peltier_defaults: str | None = None,
            **serial_kwargs,
    ):

        peltier_io = VirtualPeltierIO.from_config(port, **serial_kwargs)

        return cls(peltier_io=peltier_io, address=address, name=name, peltier_defaults=peltier_defaults)