from __future__ import annotations

from pydantic import BaseModel


class ComponentInfo(BaseModel):
    """Metadata associated with flowchem components."""

    name: str = ""
    owl_subclass_of: str = "http://purl.obolibrary.org/obo/OBI_0000968"  # 'device'
