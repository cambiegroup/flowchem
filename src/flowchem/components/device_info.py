from pydantic import AnyHttpUrl, BaseModel

from flowchem import __version__
from flowchem.utils.people import Person


class DeviceInfo(BaseModel):
    """Metadata associated with hardware devices."""

    manufacturer: str = ""
    model: str = ""
    version: str = ""
    serial_number: str | int = "unknown"
    components: dict[str, AnyHttpUrl] = {}
    backend: str = f"flowchem v. {__version__}"
    authors: list[Person] = []
    additional_info: dict = {}
