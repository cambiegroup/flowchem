from ord_schema.proto import reaction.proto
from typing import Optional
from flowchem.components.stdlib import Vessel


class VesselChemicals(Vessel):
    """
    A Vessel with additional properties for chemical identity
    """

    metadata = {
        "author": [
            {
                "first_name": "Dario",
                "last_name": "Cambie",
                "email": "dario.cambie@mpikg.mpg.de",
                "institution": "Max Planck Institute of Colloids and Interfaces",
                "github_username": "dcambie",
            }
        ],
        "stability": "beta",
        "supported": True,
    }

    def __init__(self, description: Optional[str] = None, name: Optional[str] = None, ):
        super().__init__(name=name, description=description)
        # TODO: add more properties according to ORD
