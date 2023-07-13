"""Knauer dad component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.sensors.photo import PhotoSensor

if TYPE_CHECKING:
    from flowchem.devices.knauer.dad import KnauerDAD
from flowchem.components.technical.power import PowerSwitch


class KnauerDADLampControl(PowerSwitch):
    hw_device: KnauerDAD

    def __init__(self, name: str, hw_device: KnauerDAD) -> None:
        """A generic Syringe pump."""
        super().__init__(name, hw_device)
        self.lamp = name
        self.add_api_route("/lamp_status", self.get_lamp, methods=["GET"])
        self.add_api_route("/status", self.get_status, methods=["GET"])

    async def get_status(self) -> str:
        """Get status of the instrument."""
        return await self.hw_device.status()

    async def get_lamp(self):
        """Lamp status."""
        return await self.hw_device.lamp(self.lamp)
        # return {

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

    def __init__(self, name: str, hw_device: KnauerDAD, channel: int) -> None:
        """Create a DADControl object."""
        super().__init__(name, hw_device)
        self.channel = channel

        # additional parameters
        self.add_api_route("/set-wavelength", self.set_wavelength, methods=["PUT"])
        self.add_api_route(
            "/set-integration-time",
            self.set_integration_time,
            methods=["PUT"],
        )
        self.add_api_route("/set-bandwidth", self.set_bandwidth, methods=["PUT"])

        # Ontology: diode array detector
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/CHMO_0002503",
        )

    async def calibrate_zero(self):
        """re-calibrate the sensors to their factory zero points."""
        await self.hw_device.set_signal(self.channel)

    async def acquire_signal(self) -> float:
        """Read from sensor, result to be expressed in % (optional)."""
        return await self.hw_device.read_signal(self.channel)

    async def set_wavelength(self, wavelength: int):
        """Set acquisition wavelength (nm) in the range of 0-999 nm."""
        return await self.hw_device.set_wavelength(self.channel, wavelength)

    async def set_integration_time(self, int_time: int):
        """Set integration time in the range of 10 - 2000 ms."""
        return await self.hw_device.integration_time(int_time)

    async def set_bandwidth(self, bandwidth: int):
        """Set bandwidth in the range of 4 to 25 nm."""
        return await self.hw_device.bandwidth(bandwidth)

    async def set_shutter(self, status: str):
        """Set the shutter to "CLOSED" or "OPEN" or "FILTER"."""
        return await self.hw_device.shutter(status)

    async def power_on(self) -> str:
        """Check the lamp status."""
        return f"d2 lamp is {await self.hw_device.lamp('d2')}; halogen lamp is {await self.hw_device.lamp('hal')}"

    async def power_off(self) -> str:
        """Deactivate the measurement channel."""
        reply = await self.hw_device.set_wavelength(self.channel, 0)
        return reply
