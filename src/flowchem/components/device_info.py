from pydantic import BaseModel, AnyHttpUrl

from flowchem import __version__


class Person(BaseModel):
    name: str
    email: str


class DeviceInfo(BaseModel):
    """Metadata associated with hardware devices."""

    manufacturer: str = ""
    model: str = ""
    version: str = ""
    serial_number: str | int = "unknown"
    components: list[AnyHttpUrl] = []
    backend: str = f"flowchem v. {__version__}"
    authors: list[Person] = []
    additional_info: dict = {}
