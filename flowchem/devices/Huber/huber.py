"""
Driver for Huber chillers.
"""
import logging
import aioserial
import asyncio


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
        rep = await chiller.send_command_and_read_reply("test")
        return rep


    chiller = Huber(aioserial.AioSerial(port='COM3', baudrate=9600))
    coro = main(chiller)
    asyncio.run(coro)
