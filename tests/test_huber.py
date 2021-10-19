import aioserial
import pytest
from flowchem.devices.Huber.huberchiller import HuberChiller, ChillerStatus


class FakeSerial(aioserial.AioSerial):
    """ Mock AioSerial. """
    def __init__(self):
        self.fixed_reply = None
        self.last_command = b""
        self.map_reply = {
            b"{M0A****\r\n": b"{S0AFFFF",
        }

    async def write_async(self, text: bytes):
        self.last_command = text

    async def readline_async(self,  size: int = -1) -> bytes:
        if self.fixed_reply:
            return self.fixed_reply
        return self.map_reply[self.last_command]


@pytest.fixture(scope="session")
def chiller():
    """ Chiller instance connected to FakeSerial """
    return HuberChiller(FakeSerial())


@pytest.mark.asyncio
async def test_status(chiller):
    stat = await chiller.status()
    print(stat)
    assert stat == ChillerStatus("1111111111111111")
