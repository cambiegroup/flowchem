"""Generic valve."""
from __future__ import annotations

from pydantic import BaseModel

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.exceptions import InvalidConfigurationError

# valve info can stay like that id say
class ValveInfo(BaseModel):
    ports: list[str]
    positions: dict[str, list[tuple[str, str]]]


class Valve(FlowchemComponent):
    """An abstract class for devices of type valve.

    .. warning::
        Device objects should not directly generate components with this object but rather a more specific valve type,
        such as `InjectionValve` or `MultiPositionValve`.

    All valves are characterized by:

    - a `positions` attribute, which is a set of strings representing the valve positions.
    - a `set_position()` method # here i disagree, that is a simple approach incorporating tacit knowledge
    - a `get_position()` method

    Instead:
    - 'connect()'
    - 'get_connection'
    This is explicit and informative in itself and requires no further intermittant helper mappings
    """

    def __init__(
        self,
        name: str,
        hw_device: FlowchemDevice,
        stator_ports: [(), ()],
        rotor_ports: [(), ()],
    ) -> None:
        """Create a valve object.

        Args:
        ----
            name: device name, passed to FlowchemComponent.
            hw_device: the object that controls the hardware.
            positions: list of string representing the valve ports. The order in the list reflect the physical world.
                       This potentially enables to select rotation direction to avoid specific interactions.
        """
        # a valve consists of a rotor and a stator. Solenoid valves Are special cases and can be decomposed into
        # Open/closed valves, need not be treated here but could be simulated by a [1,2,None] and rotor [3,3,None]
        self._rotor_ports = None#[(1,2,3,4,5,6),(0,)]
        self._stator_ports = None#[(7, None, None, None, None, None),(7,)]

        #bwe can infer
        super().__init__(name, hw_device)

        self.add_api_route("/position", self.get_position, methods=["GET"])
        self.add_api_route("/position", self.set_position, methods=["PUT"])
        self.add_api_route("/connections", self.connections, methods=["GET"])

# these need to go
    # async def get_position(self) -> str:  # type: ignore
    #     """Get the current position of the valve."""
    #     ...
    #
    # async def set_position(self, position: str) -> bool:
    #     """Set the valve to the specified position."""
    #     assert position in self._positions
    #     return True

    def _create_connections(self):
        # this is where the heart of logic will sit
        connections = {}
        _connections_per_position = {}
        if len(self._rotor_ports) != len(self._stator_ports):
            raise InvalidConfigurationError()
        if len(self._rotor_ports) == 1:
            # in case there is no 0 port, for data uniformity, internally add it.
            # strictly, the stator and rotor should reflect physical properties, so if stator has a hole in middle it
            # should have 0, but only rotor None. Sinc ethis does not impact functinality, thoroughness will be left to the user
            self._rotor_ports.append([None])
            self._stator_ports.append([None])
        # it is rather simple: we just move the rotor by one and thereby create a dicitionary
        for _ in range(len(self._rotor_ports[0])):
            rotor_curr = self._rotor_ports[0][_:] + self._rotor_ports[0][0:_]
            for rotor_position, stator_position in zip(rotor_curr[0]+self._rotor_ports[1], self._stator_ports[0]+self._stator_ports[1]):
                # rotor acts as dictionary keys, take into account the [1] position for connecting the 0
                # if dict key exists, instead of overwriting, simply append
                # get rid of the keys, values are the connected ports in each position
                try:
                    _connections_per_position[rotor_position].append(stator_position)
                except KeyError:
                    _connections_per_position[rotor_position] = [stator_position]


    def _change_connections(self):
        # rule how to get from one position to the next, eg by +=1 or by degrees -> this allows for mapping of
        # connections to valve command parameters
        pass

    def _initial_connection(self):
        # to apply change connections, we need some reference point, this will be, if possible: connection(0,1), but
        # without any other open connection (to 0 and 1) and if not possible connection (1,2)
        pass

    def connect_positions(self, poitions_to_connect:tuple, potions_not_to_connect:tuple):
        # check if this is possible given the mapping
        pass

    def get_position_connections(self):
        # output all positions that are currently connected
        pass

    def connections(self) -> ValveInfo:
        """Get the list of all available positions for this valve.

        This can be used for debugging, since it informs which position(implicit valve-specific string) connects which ports
        """
        return ValveInfo(ports=self._ports, positions=self._positions)

    # I kind of disagree, human friendly is misleading in this aspect
    # the human friendly approach is just needed because we are used to it, however, there is a simple solution that
    # allows to map human-friendly and graph applicable to the physical world. More concrete: If we have an injection
    # valve, we need to look at the specific valve and need to decide what inject and load mean, given the current
    # connections, which requires some transfer. My suggestion is: Instead of going to positions, specify which ports to
    # connect. In case of a simple multiposition valve, it always connects the always open port to the requested port.
    # But there are more complex rotors available, already with an injection valve: connect((1, 2)) would be more neat.
    # What is even more important, one can specify which ports to not connect (optionally during switching) but when
    # connected. This issue arose with hamilton valves, where some positions connect 3 ports and it is very hard to
    # foresee what command does what. SO here a simple connect((1,2)) would be great.

    # In order for that to work, and to make the coding and usage simple and concise, some definitions are needed:
    # 1) The port zero can exist, but does not necessarily. I advocate it to be the one on the valve turning axis, the
    #   port that on some valves is always open
    # 2) from there, one goes up, and yes that means simply looking up at the physical valve. The port straight on top
    #   of port zero is port 1
    # 3) If there is no port straight on top, then one goes in clockwise direction, until a port comes
    # 4 )Beware: For logical reasons, we need to introduce ports of "number" None. These are needed because we need to
    #   define dead-ends. These dead-ends are IMMUTABLE dead-ends, so the stator or rotor do not have a opneing there
    # 5) Mutable dead-ends: blanking plugs are treated as port number, the consumer needs to deal with its definition by
    #   graph or similar
    # Dead-ends are needed because we represent valves as graphs, edges are represented by same numbers shared. If a
    # port does not connect to anything, we set it None. There is 1 example where that is strictly needed for the logic
    # to work: Again the hamilton, it will become clear why. So much now: The rotor has more open positions than the
    # stator. Actually, Any time there is a different amount of positions on rotor and stator, this will be needed.

        # # set those via property, in course make sure that those are the same length and do all required magic
        # # 6-way valve
        # self._rotor_ports = [(1,2,3,4,5,6),(0,)]
        # self._stator_ports = [(7, None, None, None, None, None),(7,)]
        #
        # # injection valve
        # self._rotor_ports = [(1, 2, 3, 4, 5, 6), ()]
        # self._stator_ports = [(7, 7, 8, 8, 9, 9), ()]
        #
        # # hamilton right valve
        # self._rotor_ports = [(None, 1, 2, 3,), (0,)]
        # self._stator_ports = [(4, 4, 5, 5), (4,)]

