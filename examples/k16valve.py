import asyncio

from flowchem import Knauer16PortValve

DELAY = 60 * 60
START_POSITION = 10


async def main():
    valve = Knauer16PortValve(ip_address="192.168.1.122")
    await valve.initialize()

    position = START_POSITION

    while True:
        await valve.switch_to_position(str(position))
        await asyncio.sleep(DELAY)
        position += 1
        if position > 16:
            position = 1


if __name__ == '__main__':
    asyncio.run(main())
    input()
