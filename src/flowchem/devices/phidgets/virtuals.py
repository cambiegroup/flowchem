from .bubble_sensor import PhidgetBubbleSensor, PhidgetPowerSource5V
from .pressure_sensor import PhidgetPressureSensor
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
import pint


class VirtualPhidgetBubbleSensor(PhidgetBubbleSensor):

    def __init__(
            self,
            vint_serial_number: int = -1,
            vint_hub_port: int = -1,
            vint_channel: int = -1,
            phidget_is_remote: bool = False,
            data_interval: int = 250,  # ms
            name: str = "",
    ) -> None:

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Phidget",
            model="Virtual VINT",
            serial_number=vint_serial_number,
        )

        self.name = name
        self.components = []
        self._voltage = 0.0

    def __del__(self):
        ...

    async def power_on(self):
        ...

    async def power_off(self):
        ...

    def read_voltage(self) -> float:
        return self._voltage

    def read_intensity(self) -> float:
        return 0.0

    def set_dataInterval(self, datainterval: int) -> None:
        ...


class VirtualPhidgetPowerSource5V(PhidgetPowerSource5V):

    def __init__(
            self,
            vint_serial_number: int = -1,
            vint_hub_port: int = -1,
            vint_channel: int = -1,
            phidget_is_remote: bool = False,
            name: str = "",
    ) -> None:

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Phidget",
            model="Virtual VINT",
            serial_number=vint_serial_number,
        )

        self.name = name
        self.components = []

    def __del__(self):
        ...

    async def power_on(self):
        ...

    async def power_off(self):
        ...


class VirtualPhidgetPressureSensor(PhidgetPressureSensor):

    def __init__(
            self,
            pressure_range: tuple[str, str] = ("0 bar", "10 bar"),
            vint_serial_number: int = -1,
            vint_channel: int = -1,
            phidget_is_remote: bool = False,
            name: str = "",
    ) -> None:
        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="Virtual Phidget",
            model="Virtual VINT",
            serial_number=vint_serial_number,
        )

        self.name = name
        self.components = []
        self._pressure = "0.0 bar"

        # Sensor range
        sensor_min, sensor_max = pressure_range
        self._min_pressure = ureg.Quantity(sensor_min)
        self._max_pressure = ureg.Quantity(sensor_max)

    def __del__(self):
        ...

    def read_pressure(self) -> pint.Quantity:
        return ureg.Quantity(self._pressure)
