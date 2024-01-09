"""Generic valve."""
from __future__ import annotations

from pydantic import BaseModel
import json

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.exceptions import InvalidConfigurationError, DeviceError


def return_tuple_from_input(str_or_tuple):
    # in case no input is given, required, simply return None, will be dealt with by consumer
    if not str_or_tuple:
        return None
    elif type(str_or_tuple) is str:
        parsed_input = json.loads(str_or_tuple)
        if type(parsed_input[0]) is not list:
            parsed_input = [parsed_input]
        return tuple(tuple(inner) for inner in parsed_input)
    elif type(str_or_tuple) is tuple:
        if type(str_or_tuple[0]) is not tuple:
            str_or_tuple = (str_or_tuple,)
        return str_or_tuple
    else:
        raise DeviceError("Please provide input of type '[[1,2],[3,4]]'")


def return_bool_from_input(str_or_bool):
    if type(str_or_bool) is bool:
        return str_or_bool
    elif type(str_or_bool) is str:
        if str_or_bool.lower() == "true":
            return True
        elif str_or_bool.lower() == "false":
            return False
        elif str_or_bool == "":
            return None
        else:
            raise DeviceError("Please provide input of type bool, '' or 'True' or 'False'")


class ValveInfo(BaseModel):
    """
    Model representing valve information.

    Attributes:
        ports: A list of tuples representing the available ports on the stator.
        positions: A dictionary mapping position numbers to the stator ports that are connected at this position.
    """
    ports: list[tuple]
    positions: dict[int, tuple[tuple[None | int, ...], ...]]


def all_tuples_in_nested_tuple(tuple_in: tuple[tuple[int, int], ...],
                               tuple_contains: tuple[tuple[int, int, ...], ...]) -> bool:
    """
    Checks if all requested tuples are in a tuple of tuples.

    Args:
        tuple_in: The tuples to check for.
        tuple_contains: The nested tuples to check within.

    Returns:
        bool: True if all requested tuples are found, False otherwise.
    """
    all_contained = []
    for subtuple in tuple_in:
        for supertuple in tuple_contains:
            if set(subtuple) <= set(supertuple):
                all_contained.append(True)
                break
    if len(all_contained) == len(tuple_in):
        return True
    else:
        return False


def no_tuple_in_nested_tuple(tuple_in: tuple[tuple[int, int], ...],
                             tuple_contains: tuple[tuple[int, int, ...], ...]) -> bool:
    """
    Checks if none of the requested tuples are in a tuple of tuples.

    Args:
        tuple_in: The tuples to check for.
        tuple_contains: The nested tuples to check within.

    Returns:
        bool: True if none of the requested tuples are found, False otherwise.
    """
    contains_tuple = False
    for subtuple in tuple_in:
        for supertuple in tuple_contains:
            if set(subtuple) <= set(supertuple):
                contains_tuple = True
    return not contains_tuple


class Valve(FlowchemComponent):
    """
    An abstract class for devices of type valve.

    Warning:
        Device objects should not directly generate components with this object but rather a more specific valve type,
        such as `SixPortTwoPositionValve` or `SixPortPositionValve`.

    All valves are characterized by:
    - a `connections()` method, which returns an Instance of the ValveInfo class.
    - a `set_position()` method.
    - a `get_position()` method.

    Attributes:
        _rotor_ports: The rotor ports configuration.
        _stator_ports: The stator ports configuration.
        _positions: The possible positions and their connections.
    """

    def __init__(
            self,
            name: str,
            hw_device: FlowchemDevice,
            stator_ports: [(), ()],
            rotor_ports: [(), ()],
    ) -> None:
        """Create a valve object.


        Rotor and stator are both represented like:
        ((1,2,3,4,5,6),          (0))
            radial ports       middle ports
        Ports should be equally distributed, with equally spaced angle in between. If this is not the case, add None
         for missing port

        Exemple: 4 port 5 Position Valve
        stator_ports=[(None, None, 1, None, 2, None, 3, None,), (0,)],
        rotor_ports=[(None, 5, None, None, 4, None, 4, None), (5,)],

                             1
                         * * * * *
                       *     x     *
                     *               *
                 8  *  x            -x *  2
                    *            -     *
                 7  * o-      o-     o *  3
                    *   -              *
                    *  x -           x *  4
                 6   *     -          *
                       *    -o      *
                         * * * * *
                             5

        The connection is done between port 7 and 5 and 0 (central port) and 2


        Args:
        ----
            name: Device name, passed to FlowchemComponent.
            hw_device: The object that controls the hardware.
            stator_ports: Configuration of stator ports.
            rotor_ports: Configuration of rotor ports.



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

    def _create_connections(self, stator_ports, rotor_ports):
        """
        Create possible switching states from a stator and rotor representation.

        Args:
            stator_ports: Configuration of stator ports.
            rotor_ports: Configuration of rotor ports.

        Returns:
            dict: A dictionary representing possible connections for each position.
        """
        connections = {}
        if len(rotor_ports) != len(stator_ports):
            raise InvalidConfigurationError
        if len(rotor_ports) == 1:
            # in case there is no 0 port, for data uniformity, internally add it. strictly, the stator and rotor
            # should reflect physical properties, so if stator has a hole in middle it should have 0, but only rotor
            # None. Sinc ethis does not impact functionality, thoroughness will be left to the user
            rotor_ports.append([None])
            stator_ports.append([None])
        # it is rather simple: we just move the rotor by one and thereby create a dictionary
        for _ in range(len(rotor_ports[0])):
            rotor_curr = rotor_ports[0][-_:] + rotor_ports[0][:-_]
            _connections_per_position = {}
            for rotor_position, stator_position in zip(rotor_curr + rotor_ports[1], stator_ports[0] + stator_ports[1]):
                # rotor positions act as dictionary keys, take into account the [1] position for connecting the 0
                # if dict key exists, instead of overwriting, simply append
                # if rotor is none, means there is no connection, so do not add
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

    def _change_connections(self, raw_position: int, reverse: bool = False) -> str:
        """
        Translate the raw position to the corresponding device-specific position naming.

        Args:
            raw_position: The raw position value to be translated.
            reverse: If True, performs the reverse translation (default is False).

        Returns:
            str: The translated position.
        """
        # abstract valve mapping needs to be translated to device-specific position naming. This can be eg
        # addition/subtraction of one, multiplication with some angle or mapping to letters. Needs to be implemented on
        # device level since this is device communication protocol specific
        raise NotImplementedError

    def _connect_positions(self,
                           positions_to_connect: tuple[tuple],
                           positions_not_to_connect: tuple[tuple] = None,
                           arbitrary_switching: bool = True) -> int:
        """
        Select the suitable position to create desired connections.

        Args:
            positions_to_connect: The positions to connect.
            positions_not_to_connect: The positions not to connect.
            arbitrary_switching: If True, allows arbitrary switching.

        Returns:
            int: The suitable position to create the desired connections.

        Raises:
            DeviceError: If multiple positions are found and arbitrary switching is not allowed,
                         or if no connections are possible.
        """
        possible_positions = []
        # check if this is possible given the mapping
        for key, values in self._positions.items():
            if positions_not_to_connect:
                # Check the type of the 'no_tuple_in_nested_tuple' Expected tuple[tuple[int, int], ...]
                if all_tuples_in_nested_tuple(positions_to_connect, values) and no_tuple_in_nested_tuple(
                        positions_not_to_connect, values):
                    possible_positions.append(key)
            elif all_tuples_in_nested_tuple(positions_to_connect, values):
                possible_positions.append(key)
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
            # this means length == 0, no connection possible
            raise DeviceError("Connection is not possible. The valve you selected can not connect selected ports."
                              "This can be due to exclusion of certain connections by setting positions_not_to_connect")

    async def get_position(self) -> list[list[int]]:
        """
        Get the current valve position.

        Returns:
            tuple: The current position of the valve.
        """
        if not hasattr(self, "identifier"):
            pos = await self.hw_device.get_raw_position()
        else:
            pos = await self.hw_device.get_raw_position(self.identifier)
        pos = int(pos) if pos.isnumeric() else pos
        # check the type (tuple[tuple, tuple]) -> return a tuple[Any,]
        return self._positions[int(self._change_connections(pos, reverse=True))]

    async def set_position(self,
                           connect: str = "",
                           disconnect: str = "",
                           ambiguous_switching: str | bool = False):
        """
        Move the valve to the position that connects the specified ports.

        Args:
            connect: Ports to connect.
            disconnect: Ports to disconnect.
            ambiguous_switching: If True, allows ambiguous switching.
        """
        connect=return_tuple_from_input(connect)
        disconnect=return_tuple_from_input(disconnect)
        ambiguous_switching=return_bool_from_input(ambiguous_switching)
        target_pos = self._connect_positions(positions_to_connect=connect, positions_not_to_connect=disconnect,
                                             arbitrary_switching=ambiguous_switching)
        target_pos = self._change_connections(target_pos)
        if not hasattr(self, "identifier"):
            await self.hw_device.set_raw_position(target_pos)
        else:
            await self.hw_device.set_raw_position(target_pos, target_component=self.identifier)


    def connections(self) -> ValveInfo:
        """
        Get the list of all available positions for this valve.

        Returns:
            ValveInfo: The ValveInfo object containing ports and positions.
        """
        return ValveInfo(ports=self._stator_ports, positions=self._positions)

    # Philosophy: explicitly specify which ports to connect
    # In case of a simple multiposition valve, it always connects the always open central port to the requested port.
    # But there are more complex rotors available, already with an injection valve: connect((1, 2)) is concise and clear.
    # What is even more important, one can specify which ports to not connect (optionally during switching)
    # This issue is most pressing with hamilton valves, where some positions connect 3 ports and it is very hard to
    # foresee what command does what. SO here a simple connect((1,2)) helps.
    # In order for that to work, and to make the coding and usage simple and concise, some definitions are needed:
    # 1) The port zero can exist, but does not necessarily.
    #    For nomenclature reasons, port zero is the one the turning axis and only this one. COmmonly, this port,
    #    if existing, is always open
    # 2) At the physical valve, the upmost is port 1
    #   a) If there is no port straight on top, then one goes in clockwise direction, until a port comes, which is then one
    # 3 )Beware: For logical reasons, we need to introduce ports of "number" None. These are needed because we need to
    #   define dead-ends. These dead-ends are IMMUTABLE dead-ends, so the stator or rotor do not have an opening there
    #   Any time there is a different amount of positions on rotor and stator, Noneports are introduced
    # 5) Mutable dead-ends: blanking plugs are treated as port number, the consumer needs to deal with its definition by
    #   graph or similar since blanking plugs on valve side could be open
    # Dead-ends are needed because we represent valves as graphs, edges are represented by same numbers shared. If a
    # port does not connect to anything, we set it None. There is 1 example where that is strictly needed for the logic
    # to work: Again the hamilton, it will become clear why. So much now: The rotor has more open positions than the
    # stator.
    # 6) The so far mentioned logic only strictly applies to valves facing the user with their front side, however,
    # e.g. the autosampler faces one valve with its always open port to the ground. Simply flip horizontally until it
    # faces you
