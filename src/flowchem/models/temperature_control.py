from abc import ABC

from flowchem.models.base_device import BaseDevice


class TemperatureControl(BaseDevice, ABC):
    """A generic temperature controller."""

    def __init__(self, name: str | None = None):
        super().__init__(name)

    def set_temperature(self, temp: str):
        """Set the target temperature to the given string in natural language."""
        raise NotImplementedError

    def get_temperature(self) -> float:
        """Returns temperature in Celsius."""
        raise NotImplementedError

    def target_reached(self) -> bool:
        """Returns True if the set temperature target has been reached."""
        raise NotImplementedError

    def temperature_limits(self) -> dict[str, float]:
        """Returns a dict with `min` and `max` temperature in Celsius."""
        raise NotImplementedError

    def power_on(self) -> dict[str, float]:
        """Turns on temperature control."""
        raise NotImplementedError

    def power_off(self) -> dict[str, float]:
        """Turns off temperature control."""
        raise NotImplementedError

    def get_router(self, prefix: str | None = None):
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
