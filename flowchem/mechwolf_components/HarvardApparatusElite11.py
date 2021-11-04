""" MechWolf component for Elite11 """

import mechwolf as mw
from flowchem import Elite11
from flowchem.units import AnyQuantity


class HarvardApparatusElite11(mw.Pump):
    """
    An Harvard Apparatus Elite 11 pump.
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

    def __init__(self,
                 port: str,
                 syringe_volume: AnyQuantity,
                 syringe_diameter: AnyQuantity,
                 address: int = None,
                 name: str = None):
        super().__init__(name=name)
        self.port = port
        self.syringe_volume = syringe_volume
        self.syringe_diameter = syringe_diameter
        self.address = address

        self.rate = mw._ureg.parse_expression("0 ml/min")

    async def __aenter__(self):
        self._pump = Elite11.from_config(
            port=self.port,
            diameter=self.syringe_diameter,
            syringe_volume=self.syringe_volume,
            address=self.address,
            name=self.name)
        await self._pump.initialize()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._pump.stop()
        del self._pump

    async def _update(self):
        """ Actuates flow rate changes. """
        if self.rate == 0:
            await self._pump.stop()
        else:
            await self._pump.set_infusion_rate(str(self.rate))
            await self._pump.infuse_run()
