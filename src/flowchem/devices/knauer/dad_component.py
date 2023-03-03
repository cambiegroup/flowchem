"""Knauer dad component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...components.sensors.photo import PhotoSensor

if TYPE_CHECKING:
    from flowchem.devices.knauer.dad import KnauerDAD
from flowchem.components.technical.power import PowerSwitch


class KnauerDADLampControl(PowerSwitch):
    hw_device: KnauerDAD

    def __init__(self, name: str, hw_device: KnauerDAD):
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.lamp = name
        self.add_api_route("/lamp", self.get_lamp, methods=["GET"])

    async def get_lamp(self):
        """Lamp status."""
        return await self.hw_device.lamp(self.lamp)
        # return {
        #     "d2": self.hw_device._state_d2,
        #     "hal": self.hw_device._state_hal,
        # }

    async def power_on(self):
        """Turn power on."""
        return await self.hw_device.lamp(self.lamp, "ON")

    async def power_off(self):
        """Turn off power."""
        return await self.hw_device.lamp(self.lamp, "OFF")

    async def set_lamp(self, state: str) -> str:
        return await self.hw_device.lamp(self.lamp, state)
        # match lamp_name:
        #     case "d2":
        #         await self.hw_device.d2(state)
        #     case "hal":
        #         await self.hw_device.hal(state)
        #     case _:
        #         logger.error("unknown lamp name!")


class DADChannelControl(PhotoSensor):
    hw_device: KnauerDAD

    def __init__(self, name: str, hw_device: KnauerDAD, channel: int):
        """Create a DADControl object."""
        super().__init__(name, hw_device)
        self.channel = channel

        # additional parameters
        self.add_api_route("/set-wavelength", self.power_on, methods=["PUT"])
        self.add_api_route(
            "/set-integration-time", self.set_integration_time, methods=["PUT"]
        )
        self.add_api_route("/set-bandwidth", self.set_bandwidth, methods=["PUT"])

        # Ontology: diode array detector
        self.metadata.owl_subclass_of = "http://purl.obolibrary.org/obo/CHMO_0002503"

    async def calibrate_zero(self):
        """re-calibrate the sensors to their factory zero points"""
        await self.hw_device.set_signal(self.channel)

    async def acquire_signal(self) -> float:
        """Read from sensor, result to be expressed in % (optional)."""
        return await self.hw_device.read_signal(self.channel)

    async def set_wavelength(self, wavelength: int):
        """set acquisition wavelength (nm) in the range of 0-999 nm"""
        return await self.hw_device.set_wavelength(self.channel, wavelength)

    async def set_integration_time(self, int_time: int):
        """set integration time in the range of 10 - 2000 ms"""
        return await self.hw_device.integration_time(int_time)

    async def set_bandwidth(self, bandwidth: int):
        """set bandwidth in the range of 4 to 25 nm"""
        return await self.hw_device.bandwidth(bandwidth)

    async def power_on(self) -> str:
        """check the lamp status"""
        return f"d2 lamp is {await self.hw_device.lamp('d2')}; halogen lamp is {await self.hw_device.lamp('hal')}"

    async def power_off(self) -> str:
        """deactivate the measurement channel"""
        reply = await self.hw_device.set_wavelength(self.channel, 0)
        return reply

    #
    # async def acquire_spectrum(self):
    #     """Acquire an UV/VIS signal."""
    #     pass
    #
    # async def stop(self):
    #     """Stops acquisition and exit gracefully."""
    #     pass
    #
