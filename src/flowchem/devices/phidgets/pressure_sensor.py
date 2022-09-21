"""Use Phidgets to control lab devices. So far, only 4..20mA interface for Swagelock Pressure-sensor."""
import time
import warnings

from flowchem.models.sensors.pressure_sensor import PressureSensor
from loguru import logger

try:
    from Phidget22.Devices.CurrentInput import CurrentInput, PowerSupply
    from Phidget22.Devices.Log import Log, LogLevel
    from Phidget22.PhidgetException import PhidgetException
except ImportError:
    HAS_PHIDGET = False
else:
    try:
        Log.enable(LogLevel.PHIDGET_LOG_INFO, "phidget.log")
    except OSError:
        warnings.warn(
            "Phidget22 package installed but Phidget library not found!\n"
            "Get it from https://www.phidgets.com/docs/Operating_System_Support"
        )
        HAS_PHIDGET = False
    except PhidgetException as phidget_e:
        HAS_PHIDGET = "Logging already enabled" in phidget_e.description
    else:
        HAS_PHIDGET = True

from flowchem.exceptions import InvalidConfiguration
from flowchem.units import flowchem_ureg


class PhidgetPressureSensor(PressureSensor):
    """Use a Phidget current input to translate a Swagelock 4..20mA signal to the corresponding pressure value."""

    def __init__(
        self,
        pressure_range: tuple[str, str] = ("0 bar", "10 bar"),
        vint_serial_number: int = None,
        vint_channel: int = None,
        phidget_is_remote: bool = False,
        name: str | None = None,
    ):
        """Initialize PressureSensor with the given pressure range (sensor-specific!)."""
        super().__init__(name=name)
        if not HAS_PHIDGET:
            raise InvalidConfiguration(
                "Phidget unusable: library or package not installed."
            )

        # Sensor range
        sensor_min, sensor_max = pressure_range
        self._min_pressure = flowchem_ureg(sensor_min)
        self._max_pressure = flowchem_ureg(sensor_max)
        # current meter
        self.phidget = CurrentInput()

        # Ensure connection with the right sensor (ideally these are from config)
        if vint_serial_number:
            self.phidget.setDeviceSerialNumber(vint_serial_number)
        if vint_channel:
            self.phidget.setChannel(vint_channel)

        # Fancy remote sensors?
        if phidget_is_remote:
            from Phidget22.Net import Net
            from Phidget22.PhidgetServerType import PhidgetServerType

            Net.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
            self.phidget.setIsRemote(True)

        try:
            self.phidget.openWaitForAttachment(1000)
            logger.debug("Pressure sensor connected!")
        except PhidgetException as phidget_error:
            raise InvalidConfiguration(
                "Cannot connect to sensor! Check settings..."
            ) from phidget_error

        # Set power supply to 24V
        self.phidget.setPowerSupply(PowerSupply.POWER_SUPPLY_24V)
        self.phidget.setDataInterval(200)  # 200ms

    def __del__(self):
        """Ensure connection closure upon deletion."""
        self.phidget.close()

    def get_router(self):
        """Create an APIRouter for this object."""
        router = super().get_router()
        router.add_api_route("/attached", self.is_attached, methods=["GET"])

        return router

    def is_attached(self) -> bool:
        """Whether the device is connected."""
        return bool(self.phidget.getAttached())

    def _current_to_pressure(self, current_in_ampere: float) -> str:
        """Convert current reading into pressure value."""
        mill_amp = current_in_ampere * 1000
        # minP..maxP is 4..20mA
        pressure_reading = self._min_pressure + ((mill_amp - 4) / 16) * (
            self._max_pressure - self._min_pressure
        )
        logger.debug(f"Read pressure {pressure_reading} barg!")
        return str(pressure_reading * flowchem_ureg.bar)

    def read_pressure(self, units: str | None = "bar") -> str:  # type: ignore
        """
        Read pressure from the sensor and returns with `units` (default: bar).

        This is the main class method, and it never fails, but rather return None. Why?

        Well, initialization exception are fair play, upon startup any misconfiguration
        should be addressed.
        However, during experiment execution temporarily unavailability of a datasource
        should not be critical when the sensor is readonly.
        If the P-sensor is safety-critical than an event handler should be attached to it.
        If not we can live with it, returning None and letting the caller decide what
        to do with that.
        """
        try:
            current = self.phidget.getCurrent()
            logger.debug(f"Current pressure: {current}")
        except PhidgetException:
            warnings.warn("Cannot read pressure!")
            return ""
        else:
            pressure = self._current_to_pressure(current) * flowchem_ureg.bar
            return pressure.m_as(units)


if __name__ == "__main__":
    test = PhidgetPressureSensor(
        pressure_range=("0 bar", "25 bar"),
        vint_serial_number=627768,
        vint_channel=0,
    )
    while True:
        print(test.read_pressure())
        time.sleep(1)
