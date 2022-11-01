from flowchem.models.base_device import BaseDevice


class FakeDevice(BaseDevice):
    def test(self) -> bool:
        return True

    def get_router(self, prefix: str | None = None):
        """Create an APIRouter for this object."""
        router = super().get_router(prefix)

        router.add_api_route("/test", self.test, methods=["GET"])
        return router
