from __future__ import annotations

from pydantic import BaseModel


class ComponentInfo(BaseModel):
    """Metadata associated with flowchem components."""

    name: str = ""
    parent_device: str = ""
    type: str = ""
    owl_subclass_of: list[str] = [
        "http://purl.obolibrary.org/obo/OBI_0000968",
    ]  # 'device'
    get_methods: dict[str, str] = dict()
    put_methods: dict[str, str] = dict()
    inheritance: list[str] = [""]
