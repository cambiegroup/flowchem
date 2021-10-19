"""
Driver for Huber chillers.
"""
import logging
import aioserial
import asyncio
from dataclasses import dataclass


@dataclass
class PBCommand:
    """ Class representing a PBCommand """

    command: bytes

    @property
    def decoded(self):
        return self.command.decode("ascii")

    def validate(self):
        """ Check command structure to be compliant with PB format """
        # 10 characters
        assert len(self.command) == 10
        # Starts with {
        assert self.decoded[0] == "{"
        # M for master (commands) S for slave (replies).
        assert self.decoded[1] in ("M", "S")
        # Address, i.e. the desired function. Hex encoded.
        assert 0 <= int(self.decoded[2:4], 16) < 256
        # Value
        assert self.decoded[4:8] == "****" or 0 <= int(self.decoded[4:8], 16) <= 65536
        # EOL
        assert self.command[8:10] == "\r\n"


class Huber:
    """
    Control class for Huber chillers.
    """
    def __init__(self, aio: aioserial.AioSerial):
        self._serial = aio

    async def send_command_and_read_reply(self, command: str) -> str:
        await self._serial.write_async(command.encode("ascii"))
        reply = await self._serial.readline_async()
        return reply.decode("ascii")


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    async def main(chiller: Huber):
        rep = await chiller.send_command_and_read_reply("{M0007D0")
        return rep


    chiller = Huber(aioserial.AioSerial(port='COM1'))
    coro = main(chiller)
    asyncio.run(coro)
