from flowchem.components.device_info import DeviceInfo
from flowchem.devices.custom.peltier_cooler import PeltierCooler, PeltierIO, PeltierCommand, PeltierCommands
from flowchem.utils.people import samuel_saraiva
from loguru import logger
import asyncio
import pint


class Serial:
    port = "Fake"


class VirtualPeltierIO(PeltierIO):

    def __init__(self):
        # Initialize the parent class with a dummy serial port

        # Simulated state variables
        self._temperature = 25.0  # Simulated temperature in °C
        self._sink_temperature = 25.0  # Simulated sink temperature in °C
        self._power = 0.0  # Simulated power in W
        self._current = 0  # Simulated current in A
        self._is_on = False  # Simulated state (on/off)
        self._setpoint = 25.0  # Simulated setpoint temperature in °C
        self._serial = Serial()

    @classmethod
    def from_config(cls, port, **serial_kwargs):
        return cls()

    async def _write(self, command: PeltierCommand):
        command_compiled = command.compile()
        logger.debug(f"Sending virtual command: {repr(command_compiled)}")

    async def _read_reply(self, command: PeltierCommand) -> str:
        """Simulate reading a reply from the virtual device."""
        logger.debug(f"Virtual Peltier generating reply for command: {command.compile()}")

        if command.command_string == "GT1":  # Get temperature
            return f"{self._temperature}"
        elif command.command_string == "GT2":  # Get sink temperature
            return f"{self._sink_temperature}"
        elif command.command_string == "STV":  # Set temperature
            self._setpoint = float(command.command_argument) / 100
            return f"{self._setpoint}"
        elif command.command_string == "SEN":  # Switch on
            self._is_on = True
            return "1"
        elif command.command_string == "SDI":  # Switch off
            self._is_on = False
            return "0"
        elif command.command_string == "GCU":  # Get power
            return f"{self._power}"
        elif command.command_string == "GPW":  # Get current
            return f"{self._current}"
        else:
            return "0"

    async def write_and_read_reply(self, command: PeltierCommand) -> str:
        """Simulate sending a command and reading the reply."""
        await self._write(command)
        response = await self._read_reply(command)
        return response


class VirtualPeltierCooler(PeltierCooler):

    def __init__(self,
                 peltier_io: PeltierIO,
                 name: str = "",
                 address: int = 0,
                 peltier_defaults: str | None = None):

        super().__init__(peltier_io=peltier_io,
                         name=name,
                         address=address,
                         peltier_defaults=peltier_defaults)

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Manufacturer",
            model="Virtual Peltier Cooler",
        )

        self.current_temperature = 0
        self.power = 0

    @classmethod
    def from_config(
            cls,
            port: str,
            address: int,
            name: str = "",
            peltier_defaults: str | None = None,
            **serial_kwargs,
    ):

        peltier_io = VirtualPeltierIO.from_config(port, **serial_kwargs)
        logger.info(f"Connected to virtual Peltier Cooler: {name} at address {address}")
        return cls(peltier_io=peltier_io, address=address, name=name, peltier_defaults=peltier_defaults)

    async def set_temperature(self, temperature: pint.Quantity):
        """ Override set_temperature to simulate temperature changes. """
        self.current_temperature = temperature.m_as("°C")
        logger.debug(f"Virtual temperature set to {self.current_temperature} °C")
        await asyncio.sleep(0.01)

    async def get_temperature(self) -> float:
        """ Override get_temperature to return the simulated value. """
        return self.current_temperature

    async def get_power(self) -> float:
        """ Override get_power to return a simulated power value. """
        return self.power

    async def _set_current_limit_cooling(self, current_limit: float):
        # current in amp
        await self.send_command_and_read_reply(PeltierCommands.COOLING_CURRENT_LIMIT, round(current_limit * 100))

    async def _set_current_limit_heating(self, current_limit: float):
        # current in amp
        await self.send_command_and_read_reply(PeltierCommands.HEATING_CURRENT_LIMIT, round(current_limit * 100))

    async def _set_d_of_pid(self, differential: float):
        # max 10
        await self.send_command_and_read_reply(PeltierCommands.SET_DIFFERENTIAL_PID, round(differential * 100))

    async def _set_i_of_pid(self, integral):
        # max 10
        await self.send_command_and_read_reply(PeltierCommands.SET_INTEGRAL_PID, round(integral * 100))

    async def _set_p_of_pid(self, proportional):
        # max 10
        await self.send_command_and_read_reply(PeltierCommands.SET_PROPORTIONAL_PID, round(proportional * 100))

    async def _set_max_temperature(self, t_max):
        # max 10
        await self.send_command_and_read_reply(PeltierCommands.SET_T_MAX, round(t_max * 100))

    async def _set_min_temperature(self, t_min):
        # max 10
        await self.send_command_and_read_reply(PeltierCommands.SET_T_MIN, round(t_min * 100))


async def main():
    from flowchem import ureg
    # Create a virtual PeltierCooler instance
    virtual_peltier = VirtualPeltierCooler.from_config(port="COMX", name="Virtual Peltier", address=0)

    # Initialize the virtual device
    await virtual_peltier.initialize()

    # Set a temperature and read it back
    await virtual_peltier.set_temperature(ureg.Quantity("10 °C"))
    current_temp = await virtual_peltier.get_temperature()
    print(f"Current temperature: {current_temp} °C")

    # Turn off the virtual device
    await virtual_peltier.stop_control()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
