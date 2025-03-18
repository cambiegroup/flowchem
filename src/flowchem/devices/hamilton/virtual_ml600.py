from flowchem.devices.hamilton.ml600 import (HamiltonPumpIO, ML600, Protocol1Command, ML600Commands, ML600Pump,
                                               ML600LeftValve)
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import aioserial
import asyncio
import pint


class VirtualHamiltonPumpIO(HamiltonPumpIO):
    """Virtual HamiltonPumpIO class to simulate the behavior of the real Hamilton ML600 syringe pump."""

    def __init__(self):
        # Initialize the parent class with a dummy serial port
        self._serial = "Fake"
        self.num_pump_connected = None

        # Simulated state variables
        self._is_running = False  # Simulated state (running/not running)
        self._last_command = ""  # Simulated last executed command
        self._current_volume = 1.0  # Simulated current syringe volume in ml
        self._valve_position = "I"  # Simulated valve position (I = Inlet, O = Outlet, W = Wash)
        self._pump_status = False  # Simulated pump status (False = idle, True = busy)
        self._valve_status = False  # Simulated valve status (False = idle, True = busy)

    async def _write_async(self, command: bytes):
        """Simulate writing a command to the virtual device."""
        logger.debug(f"Virtual Hamilton ML600 received command: {command.decode('ascii')}")

    async def _read_reply_async(self) -> str:
        """Simulate reading a reply from the virtual device."""
        logger.debug(f"Virtual Hamilton ML600 generating reply for command: {self._last_command}")
        return "0"

    async def write_and_read_reply_async(self, command: Protocol1Command) -> str:
        """Simulate sending a command and reading the reply."""
        self._last_command = command.compile()
        await self._write_async(self._last_command.encode("ascii"))
        response = await self._read_reply_async()
        return response


class VirtualML600(ML600):
    """Virtual ML600 class to simulate the behavior of the real Hamilton ML600 syringe pump."""

    def __init__(
        self,
        pump_io: HamiltonPumpIO,
        syringe_volume: str,
        name: str,
        address: int = 1,
        **config,
    ) -> None:


        # Call the parent class constructor with the virtual HamiltonPumpIO
        super().__init__(pump_io, syringe_volume, name, address, **config)

        # Override device info for virtual device
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Hamilton",
            model="Virtual ML600",
        )

    @classmethod
    def from_config(cls, **config):
        # Initialize the virtual HamiltonPumpIO
        virtual_pump_io = VirtualHamiltonPumpIO()
        return cls(
            virtual_pump_io,
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
        )

    async def initialize(self, hw_init=False, init_speed: str = "200 sec / stroke"):
        """Simulate initializing the virtual ML600 pump."""
        logger.info(f"Virtual ML600 {self.name} initialized!")
        self.dual_syringe = False  # Simulate single syringe system
        self.components.extend([ML600Pump("pump", self), ML600LeftValve("valve", self)])

    async def send_command_and_read_reply(self, command: Protocol1Command) -> str:
        """Simulate sending a command to the virtual pump."""
        return await self.pump_io.write_and_read_reply_async(command)

    async def get_current_volume(self, pump: str) -> pint.Quantity:
        """Return current syringe position in ml."""
        return ureg.Quantity(f"{self.pump_io._current_volume} ml")

    async def set_to_volume(self, target_volume: pint.Quantity, rate: pint.Quantity, pump: str):
        """Simulate setting the syringe to a target volume."""
        self.pump_io._current_volume = target_volume.m_as("ml")
        logger.debug(f"Virtual ML600 {self.name} set to volume {target_volume} at rate {rate}")
        return True

    async def get_valve_position_by_name(self, valve: ML600Commands) -> str:
        """Simulate getting the valve position by name."""
        return self.pump_io._valve_position

    async def set_valve_position_by_name(self, valve: ML600Commands, target_position: str, wait_for_movement_end: bool = True):
        """Simulate setting the valve position by name."""
        self.pump_io._valve_position = target_position
        logger.debug(f"Virtual ML600 {self.name} valve position set to {target_position}")
        return True

    async def get_pump_status(self, pump: str = "") -> bool:
        """Simulate getting the pump status."""
        return self.pump_io._pump_status

    async def get_valve_status(self, valve: str = "") -> bool:
        """Simulate getting the valve status."""
        return self.pump_io._valve_status

    async def get_raw_position(self, target_component: str) -> str:
        return "1"


async def main():
    # Create a virtual ML600 instance
    virtual_ml600 = VirtualML600.from_config(port="COMX", name="Virtual ML600", syringe_volume="5 mL")

    # Initialize the virtual device
    await virtual_ml600.initialize()

    # Set the syringe to a target volume
    await virtual_ml600.set_to_volume(ureg.Quantity("0.5 mL"), ureg.Quantity("1 mL/min"), "B")

    # Get the current volume
    current_volume = await virtual_ml600.get_current_volume("B")
    print(f"Current volume: {current_volume}")

    # Set the valve position
    await virtual_ml600.set_valve_position_by_name(ML600Commands.VALVE_BY_NAME_CW, "O")

    # Get the valve position
    valve_position = await virtual_ml600.get_valve_position_by_name(ML600Commands.VALVE_BY_NAME_CW)
    print(f"Valve position: {valve_position}")

    valve_position = await virtual_ml600.components[1].get_position()

    print(valve_position)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())