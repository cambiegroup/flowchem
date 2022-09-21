from abc import ABC

from flowchem.models.base_device import BaseDevice


class TemperatureControl(BaseDevice, ABC):
    """A generic temperature controller."""

    def get_router(self, prefix: str | None = None):
        router = super().get_router()
        # FIXME add
        # sensor temperature API in sub-prefix
        # set-temperature
        # is-temperature-reached
        # min-temp
        # max-temp
        return router
