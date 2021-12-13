""" LTF reactors """
from typing import Optional

from components.stdlib import Channel, YMixer
from flowchem.components.properties import Component, MappedComponentMixin


class LTF_HTM_ST_3_1(MappedComponentMixin, Component):
    """ An LTF HTM ST 3 1 reactor. """

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self.mapping = {"INLET_1", "INLET_2", "QUENCHER", "OUTLET"}

        inlet1 = Channel(name="INLET_1", length="10 mm", volume="8 ul", material="glass")
        inlet2 = Channel(name="INLET_2", length="10 mm", volume="8 ul", material="glass")
        mixer_inlet = YMixer()
        reactor1 = Channel(name="REACTOR", length="60 mm", volume="58 ul", material="glass")
        quencher = Channel(name="QUENCHER", length="15 mm", volume="10 ul", material="glass")
        mixer_quencher = YMixer()
        reactor2 = Channel(name="REACTOR2", length="40 mm", volume="46 ul", material="glass")
        outlet = Channel(name="OUTLET", length="10 mm", volume="28 ul", material="glass")

        self.nodes = [inlet1, inlet2, mixer_inlet, reactor1, quencher, mixer_quencher, reactor2, outlet]
        self.edges = [
            (inlet1, mixer_inlet),
            (inlet2, mixer_inlet),
            (mixer_inlet, reactor1),
            (reactor1, mixer_quencher),
            (quencher, mixer_quencher),
            (mixer_quencher, reactor2),
            (reactor2, outlet)
        ]