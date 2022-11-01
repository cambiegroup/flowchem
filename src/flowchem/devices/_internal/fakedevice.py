"""Fake device for testing purposes. No parameters needed."""
from flowchem.models.base_device import BaseDevice


class FakeDevice(BaseDevice):
    def get_router(self, prefix: str | None = None):
        """Create an APIRouter for this object."""
        router = super().get_router(prefix)

        router.add_api_route("/test", lambda f: True, methods=["GET"])
        return router
