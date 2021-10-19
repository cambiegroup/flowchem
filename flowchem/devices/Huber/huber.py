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

    command: str

    def to_chiller(self) -> bytes:
        self.validate()
        return self.command.encode("ascii")

    def validate(self):
        """ Check command structure to be compliant with PB format """
        # 10 characters
        assert len(self.command) == 10
        # Starts with {
        assert self.command[0] == "{"
        # M for master (commands) S for slave (replies).
        assert self.command[1] in ("M", "S")
        # Address, i.e. the desired function. Hex encoded.
        assert 0 <= int(self.command[2:4], 16) < 256
        # Value
        assert self.command[4:8] == "****" or 0 <= int(self.command[4:8], 16) <= 65536
        # EOL
        assert self.command[8:10] == "\r\n"

    @property
    def data(self):
        return self.command[4:8]

    @property
    def is_reply(self):
        return self.command[1] == "S"

    def parse_temperature(self):
        self.data


class Huber:
    """
    Control class for Huber chillers.
    """
    def __init__(self, aio: aioserial.AioSerial):
        self._serial = aio

    async def get_temperature(self) -> float:
        reply = await self.send_command_and_read_reply("{M00****")
        pb_reply = PBCommand(reply)
        return pb_reply.parse_temperature(reply[4:8])

    async def send_command_and_read_reply(self, command: str) -> str:
        # If newline is forgotten add it :D
        if len(command) == 8:
            command += "\r\n"
        pb_command = PBCommand(command)
        await self._serial.write_async(pb_command.to_chiller())
        reply = await self._serial.readline_async()
        return reply.decode("ascii")


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    async def main(chiller: Huber):
        rep = await chiller.send_command_and_read_reply("{M0007D0\r\n")
        return rep


    chiller = Huber(aioserial.AioSerial(port='COM1'))
    coro = main(chiller)
    x = asyncio.run(coro)
    print(x)
