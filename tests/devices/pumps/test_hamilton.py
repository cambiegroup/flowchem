# import asyncio
# import sys
#
# import aioserial
# import pytest
# from fastapi import FastAPI
# from httpx import AsyncClient
#
# from flowchem.server.api_server import create_server_for_devices
# from flowchem.server.configuration_parser import instantiate_device
#
#
# class FakeSerial(aioserial.AioSerial):
#     """Mock AioSerial."""
#
#     # noinspection PyMissingConstructor
#     def __init__(self):
#         self.fixed_reply = None
#         self.last_command = b""
#         self.map_reply = {
#             b"aUR\r": b"\x06NV01.01.a",
#             b"1a\r": b"1",
#             b"bUR\r": b"",
#             b":XR\r": b"",
#
#         }
#
#     async def write_async(self, text: bytes):
#         """Override AioSerial method"""
#         self.last_command = text
#
#     async def readline_async(self, size: int = -1) -> bytes:
#         """Override AioSerial method"""
#         if self.last_command == b"{MFFFFFF\r\n":
#             await asyncio.sleep(999)
#         if self.fixed_reply:
#             return self.fixed_reply
#         return self.map_reply[self.last_command]
#
#     def __repr__(self):
#         return "FakeSerial"
#
# @pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
# @pytest.fixture
# def devices() -> dict:
#     """ML600 device."""


#     config = {"device": {}}
#     config["device"]["ml600-test"] = {
#         "type": "ML600",
#         "port": mock_serial.port,
#         "syringe_volume": "1 ml",
#     }
#     return instantiate_device(config)
#
#
# @pytest.fixture
# async def app(devices) -> FastAPI:
#     """ML600-containing app."""
#     app = await create_server_for_devices(devices)
#
#     # Ugly workaround, essentially startup hooks are not called with AsyncClient
#     # See tiangolo/fastapi#2003 for details
#     [await dev.initialize() for dev in devices["device"]]
#
#     return app["api_server"]
#
#
# @pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
# @pytest.mark.anyio
# async def test_root(app):
#     """Test root verifies app initialization (config validation/ML600 instantiation)."""
#     async with AsyncClient(app=app, base_url="http://127.0.0.1:8000") as ac:
#         response_root = await ac.get("/")
#         response_docs = await ac.get("/docs")
#     assert response_root.status_code == 307
#     assert response_docs.status_code == 200
#
#
# @pytest.mark.skipif(sys.platform == "win32", reason="No mock_serial on windows")
# @pytest.mark.anyio
# async def test_get_position(app):
#     """Test firmware_version."""
#     async with AsyncClient(app=app, base_url="http://127.0.0.1:8000/ml600-test") as ac:
#         response = await ac.get("/pump/")
#     assert response.status_code == 200
#     assert "NV01.01.a" in response.text
