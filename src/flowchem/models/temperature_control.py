"""Temperature control, either for heating or cooling."""
from abc import ABC

from flowchem.models.base_device import BaseDevice


class TemperatureControl(BaseDevice, ABC):
    """A generic temperature controller."""

    def __init__(self, name: str | None = None):
        """Just call superclass constructor."""
        super().__init__(name)

    def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        raise NotImplementedError

    def get_temperature(self) -> float:
        """Return temperature in Celsius."""
        raise NotImplementedError

    def target_reached(self) -> bool:
        """Return True if the set temperature target has been reached."""
        raise NotImplementedError

    def temperature_limits(self) -> dict[str, float]:
        """Return a dict with `min` and `max` temperature in Celsius."""
        raise NotImplementedError

    def power_on(self) -> dict[str, float]:
        """Turn on temperature control."""
        raise NotImplementedError

    def power_off(self) -> dict[str, float]:
        """Turn off temperature control."""
        raise NotImplementedError

    def get_router(self, prefix: str | None = None):
        """Return device APIRouter."""
        router = super().get_router(prefix)

        router.add_api_route("/temperature", self.set_temperature, methods=["PUT"])
        router.add_api_route("/temperature", self.get_temperature, methods=["GET"])

        router.add_api_route("/power-on", self.power_on, methods=["PUT"])
        router.add_api_route("/power-off", self.power_off, methods=["PUT"])

        router.add_api_route("/target-reached", self.target_reached, methods=["GET"])
        router.add_api_route(
            "/temperature-limits", self.temperature_limits, methods=["GET"]
        )

        return router
