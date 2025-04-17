from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.phidgets.bubble_sensor_component import (
    PhidgetBubbleSensorComponent,
    PhidgetBubbleSensorPowerComponent,
)
from flowchem.devices.phidgets.pressure_sensor_component import PhidgetPressureSensorComponent
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
import pint


class VirtualPhidgetBubbleSensor(FlowchemDevice):

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors.append(samuel_saraiva)
        self.device_info.manufacturer="Virtual Phidget"
        self.device_info.model="Virtual BubbleSensor"

        self._voltage = 0.0

    async def initialize(self):
        self.components.append(PhidgetBubbleSensorComponent("bubble-sensor", self)) # type: ignore

    def power_on(self) -> bool:
        return True

    def power_off(self) -> bool:
        return True

    def read_voltage(self) -> float:
        return self._voltage

    def read_intensity(self) -> float:
        return 0.0

    def set_dataInterval(self, datainterval: int) -> None:
        ...


class VirtualPhidgetPowerSource5V(FlowchemDevice):

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors.append(samuel_saraiva)
        self.device_info.manufacturer = "Virtual Phidget"
        self.device_info.model = "Virtual PowerSource"

    async def initialize(self):
        self.components.append(PhidgetBubbleSensorPowerComponent("5V", self)) # type: ignore

    def power_on(self):
        ...

    def power_off(self):
        ...


class VirtualPhidgetPressureSensor(FlowchemDevice):

    def __init__(self, name: str = "", **kwargs) -> None:
        super().__init__(name)
        self.device_info.authors.append(samuel_saraiva)
        self.device_info.manufacturer = "Virtual Phidget"
        self.device_info.model = "Virtual PressureSensor"

        self._pressure = "0.0 bar"

    async def initialize(self):
        self.components.extend([PhidgetPressureSensorComponent("pressure-sensor", self)]) # type: ignore

    def read_pressure(self) -> pint.Quantity:
        return ureg.Quantity(self._pressure)
