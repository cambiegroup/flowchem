"""Generic valve."""
from __future__ import annotations

from pydantic import BaseModel

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.exceptions import InvalidConfigurationError, DeviceError


class ValveInfo(BaseModel):
    ports: list[tuple]
    positions: dict[int, tuple[tuple[int, int], ...]]


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
        self._rotor_ports = rotor_ports
        self._stator_ports = stator_ports
        self._positions = self._create_connections(self._stator_ports, self._rotor_ports)

        # bwe can infer
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

    def _create_connections(self, stator_ports, rotor_ports):
        # this is where the heart of logic will sit
        connections = {}
        if len(rotor_ports) != len(stator_ports):
            raise InvalidConfigurationError()
        if len(rotor_ports) == 1:
            # in case there is no 0 port, for data uniformity, internally add it.
            # strictly, the stator and rotor should reflect physical properties, so if stator has a hole in middle it
            # should have 0, but only rotor None. Sinc ethis does not impact functionality, thoroughness will be left to the user
            rotor_ports.append([None])
            stator_ports.append([None])
        # it is rather simple: we just move the rotor by one and thereby create a dictionary
        for _ in range(len(rotor_ports[0])):
            rotor_curr = rotor_ports[0][-_:] + rotor_ports[0][:-_]
            _connections_per_position = {}
            for rotor_position, stator_position in zip(rotor_curr + rotor_ports[1], stator_ports[0] + stator_ports[1]):
                # rotor acts as dictionary keys, take into account the [1] position for connecting the 0
                # if dict key exists, instead of overwriting, simply append
                # if rotor is none, means there is no connection, so do not even bother to add
                if rotor_position is not None:
                    try:
                        _connections_per_position[rotor_position] += (stator_position,)
                    except KeyError:
                        _connections_per_position[rotor_position] = (stator_position,)
                        # get rid of the keys, values are the connected ports in each position
            connections[_] = tuple(_connections_per_position.values())
        # lastly, trim the lists of connections that already exist
        # trim returned connections
        unique_connections = set(connections.values())
        to_delete = []
        for connection in unique_connections:
            counter = 0
            for key, value in connections.items():
                if connection == value:
                    if counter > 0:
                        to_delete.append(key)
                    counter += 1
        for _ in to_delete:
            del connections[_]

        return connections

    def _change_connections(self, raw_position, reverse: bool = False) -> str:
        # abstract valve mapping needs to be translated to device-specific position naming. This can be eg
        # addition/subtraction of one, multiplication with some angle or mapping to letters. Needs to be implemented on
        # device level
        raise NotImplementedError

    def _connect_positions(self, positions_to_connect: tuple[tuple], positions_not_to_connect: tuple[tuple] = None,
                           arbitrary_switching: bool = True) -> int:
        """
        This is the heart of valve switching logic: select the suitable position (so actually the key in
        self._positions) to create desired connections
        """
        # in order for this to work correctly:
        #   1) positions need to be sorted
        #   2) positions need to be split into elements of 2, e.g. a position that connects (1,2,3)
        #       needs to be represented as (1,2), (2,3), (1,3). This (both) can already be achieved on creation of connections

        positions_to_connect_canon = [tuple(sorted(positions)) for positions in
                                      positions_to_connect]  # tuple(sorted(positions_to_connect))
        positions_not_to_connect_canon = [tuple(sorted(positions)) for positions in positions_not_to_connect]
        possible_positions = []
        # check if this is possible given the mapping
        for position_name, connections in self._positions.items():
            # identify positions with desired connectivity
            for positions in positions_to_connect_canon:
                if positions in connections:
                    # only add the ones that do not include undesired connectivities
                    for positions_not in positions_not_to_connect_canon:
                        if positions_not not in connections:
                            possible_positions.append(position_name)
        if len(possible_positions) > 1:
            if not arbitrary_switching:
                raise DeviceError("There are multiple positions for the valve to connect your specified ports. "
                                  "Either allow arbitrary switching, or specify which connections not to connect")
            elif arbitrary_switching:
                return possible_positions[0]
            else:
                raise DeviceError
        elif len(possible_positions) == 1:
            return possible_positions[0]
        else:
            # this means length == 0
            raise DeviceError("Connection is not possible. The valve you selected can not connect selected ports."
                              "This can be due to exclusion of certain connections by setting positions_not_to_connect")


    async def get_position(self) -> tuple[tuple]:
        """Get current valve position."""
        pos = await self.hw_device.get_raw_position()
        return self._positions[int(self._change_connections(pos, reverse=True))]

    async def set_position(self, *args, **kwargs):
        """Move valve to position, which connects named ports"""
        target_pos = self._connect_positions(*args, **kwargs)
        target_pos = self._change_connections(target_pos)
        return await self.hw_device.set_raw_position(target_pos)

    def connections(self) -> ValveInfo:
        """Get the list of all available positions for this valve.

        This mainly has informative purpose
        """
        return ValveInfo(ports=self._stator_ports, positions=self._positions)

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
    #   a) If there is no port straight on top, then one goes in clockwise direction, until a port comes
    # 3 )Beware: For logical reasons, we need to introduce ports of "number" None. These are needed because we need to
    #   define dead-ends. These dead-ends are IMMUTABLE dead-ends, so the stator or rotor do not have a opneing there
    # 5) Mutable dead-ends: blanking plugs are treated as port number, the consumer needs to deal with its definition by
    #   graph or similar
    # Dead-ends are needed because we represent valves as graphs, edges are represented by same numbers shared. If a
    # port does not connect to anything, we set it None. There is 1 example where that is strictly needed for the logic
    # to work: Again the hamilton, it will become clear why. So much now: The rotor has more open positions than the
    # stator. Actually, Any time there is a different amount of positions on rotor and stator, this will be needed.
    # 6) The so far mentioned logic only strictly applies to valves which face the user with there front side, however,
    # eg the autosampler faces one valve to the ground, with its alway open port. To also include those in herein
    # developed logic/terminology, there needs to be a defined mutation. This is simply the smallest angle needed
