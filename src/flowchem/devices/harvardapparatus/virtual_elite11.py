from flowchem.devices.harvardapparatus.elite11 import Elite11, HarvardApparatusPumpIO, Protocol11Command
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from loguru import logger
import asyncio


class Serial:
    name = "COMX"

class VirtualHarvardApparatusPumpIO(HarvardApparatusPumpIO):
    """Virtual HarvardApparatusPumpIO class to simulate the behavior of the real Elite 11 syringe pump."""

    def __init__(self, port: str, **serial_kwargs):
        # Initialize the parent class with a dummy serial port

        # Simulated state variables
        self._is_running = False  # Simulated state (running/not running)
        self._last_command = ""  # Simulated last executed command
        self._current_volume = 0.0  # Simulated current syringe volume in ml
        self._flow_rate = 0.0  # Simulated flow rate in ml/min
        self._force = 30  # Simulated force in percentage
        self._syringe_diameter = 14.567  # Simulated syringe diameter in mm
        self._syringe_volume = 10.0  # Simulated syringe volume in ml
        self._target_volume = 0.0  # Simulated target volume in ml
        self._pump_status = "stopped"  # Simulated pump status (stopped, infusing, withdrawing)
        self._serial = Serial()

    async def _write_async(self, command: str):
        """Simulate writing a command to the virtual device."""
        logger.debug(f"Virtual Elite 11 received command: {command}")

    async def _read_reply_async(self) -> str:
        """Simulate reading a reply from the virtual device."""
        logger.debug(f"Virtual Elite 11 generating reply for command: {self._last_command}")

        if "diameter" in self._last_command:  # Get syringe diameter
            return f"{self._syringe_diameter} mm"
        elif "svolume" in self._last_command:  # Get syringe volume
            return f"{self._syringe_volume} ml"
        elif "FORCE" in self._last_command:  # Get force
            return f"{self._force}%"
        elif "irate" in self._last_command:  # Get infusion rate
            return f"{self._flow_rate} ml/min"
        elif "wrate" in self._last_command:  # Get withdrawal rate
            return f"{self._flow_rate} ml/min"
        elif "tvolume" in self._last_command:  # Get target volume
            return f"{self._target_volume} ml"
        elif "irun" in self._last_command:  # Start infusion
            self._pump_status = "infusing"
            return "Infusion started"
        elif "wrun" in self._last_command:  # Start withdrawal
            self._pump_status = "withdrawing"
            return "Withdrawal started"
        elif "stp" in self._last_command:  # Stop pump
            self._pump_status = "stopped"
            return "Pump stopped"
        elif "VER" in self._last_command:  # Get version
            return "11 ELITE I/W Single 3.0.4"
        else:
            return "0000"

    async def write_and_read_reply(self, command: Protocol11Command, return_parsed: bool = True) -> str | list[str]:
        """Simulate sending a command and reading the reply."""
        self._last_command = command.command
        await self._write_async(self._last_command)
        response = await self._read_reply_async()
        return [response] if return_parsed else response

    def autodiscover_address(self) -> int:
        return 1


class VirtualElite11(Elite11):
    """Virtual Elite11 class to simulate the behavior of the real Harvard Apparatus Elite 11 syringe pump."""

    def __init__(
            self,
            virtual_pump_io,
            syringe_diameter: str,
            syringe_volume: str,
            address: int = 0,
            name: str = "",
            force: int = 30,
    ) -> None:

        # Call the parent class constructor with the virtual HarvardApparatusPumpIO
        super().__init__(virtual_pump_io, syringe_diameter, syringe_volume, address, name, force)

        # Override device info for virtual device
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Harvard Apparatus",
            model="Virtual Elite 11",
        )

    @classmethod
    def from_config(
        cls,
        port: str,
        syringe_diameter: str,
        syringe_volume: str,
        address: int = -1,
        name: str = "",
        force: int = 30,
        **serial_kwargs,
    ):
        # Initialize the virtual HarvardApparatusPumpIO
        virtual_pump_io = VirtualHarvardApparatusPumpIO(port="dummy_port")
        return cls(
            virtual_pump_io,
            address=address,
            name=name,
            syringe_diameter=syringe_diameter,
            syringe_volume=syringe_volume,
            force=force,
        )

    async def is_moving(self) -> bool:
        return False

    async def set_flow_rate(self, rate: str):
        logger.info(f"Set flow rate {rate}")

    async def set_withdrawing_flow_rate(self, rate: str):
        logger.info(f"Set flow rate {rate}")


async def main():
    # Create a virtual Elite 11 instance
    virtual_elite11 = VirtualElite11.from_config(
        port="COMX",
        syringe_diameter="14.567 mm",
        syringe_volume="10 ml",
        name="Virtual Elite 11",
    )

    # Initialize the virtual device
    await virtual_elite11.initialize()

    await virtual_elite11.is_moving()

    # Start infusion
    await virtual_elite11.infuse()

    await virtual_elite11.withdraw()

    # Stop the pump
    await virtual_elite11.stop()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())