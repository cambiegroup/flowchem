import asyncio
import warnings
import math
from typing import Any, Dict, Optional, MutableMapping, List

from loguru import logger

from flowchem.units import flowchem_ureg
from flowchem.components.stdlib import Component


class ActiveComponent(Component):
    """
    A connected, controllable component.

    All components being manipulated in a `Protocol` must be of type `ActiveComponent`.

    ::: tip
    Users should not directly instantiate an `ActiveComponent` because it is an abstract base class, not a functioning laboratory instrument.
    :::

    Arguments:
    - `name`: The name of the component.

    Attributes:
    - `name`: The name of the component.

    """

    _id_counter = 0

    def __init__(self, name: Optional[str] = None):
        super().__init__(name=name)
        self._base_state: Dict[str, Any] = NotImplemented
        """
        A placeholder for the base state of the component.
        All subclasses of `ActiveComponent` must have this attribute.
        The dict must have values which can be parsed into compatible units of the object's other attributes, if applicable.
        At the end of a protocol and when not under explicit control by the user, the component will return to this state.
        """

    def _update_from_params(self, params: dict) -> None:
        """
        Updates the attributes of the object from a dict.

        Arguments:
        - `params`: A dict whose keys are the strings of attribute names and values are the new values of the attribute.
        """
        for key, value in params.items():
            if isinstance(getattr(self, key), flowchem_ureg.Quantity):
                setattr(self, key, flowchem_ureg.parse_expression(value))
            else:
                setattr(self, key, value)

    async def _update(self):
        raise NotImplementedError(f"Implement an _update() method for {repr(self)}.")

    def _validate(self, dry_run: bool) -> None:
        """
        Checks if a component's class is valid.

        Arguments:
        - `dry_run`: Whether this is a validation check for a dry run. Ignores the actual executability of the component.

        Returns:
        - Whether the component is valid or not.
        """

        logger.debug(f"Validating {self.name}...")

        # base_state method must return a dict
        if not isinstance(self._base_state, dict):
            raise ValueError("_base_state is not a dict")

        # the base_state dict must not be empty
        if not self._base_state:
            raise ValueError("_base_state dict must not be empty")

        # validate the base_state dict
        for k, v in self._base_state.items():
            if not hasattr(self, k):
                raise ValueError(
                    f"base_state sets {k} for {repr(self)} but {k} is not an attribute of {repr(self)}. "
                    f"Valid attributes are {self.__dict__}"
                )

            # dimensionality check between _base_state units and attributes
            if isinstance(self.__dict__[k], flowchem_ureg.Quantity):
                # figure out the dimensions we're comparing
                expected_dim = flowchem_ureg.parse_expression(v).dimensionality
                actual_dim = self.__dict__[k].dimensionality

                if expected_dim != actual_dim:
                    raise ValueError(
                        f"Invalid dimensionality in _base_state for {repr(self)}. "
                        f"Got {flowchem_ureg.parse_expression(v).dimensionality} for {k}, "
                        f"expected {self.__dict__[k].dimensionality}"
                    )

            # if not dimensional, do type matching
            elif not isinstance(self.__dict__[k], type(v)):
                raise ValueError(
                    f"Bad type matching for {k} in _base_state dict. "
                    f"Should be {type(self.__dict__[k])} but is {type(v)}."
                )

        # once we've checked everything, it should be good
        if not dry_run:
            self._update_from_params(self._base_state)
            logger.trace(f"Attempting to call _update() for {repr(self)}.")
            asyncio.run(self._validate_update())

        logger.debug(f"{repr(self)} is valid")

    async def _validate_update(self):
        async with self:
            res = await self._update()
            if res is not None:
                raise ValueError(f"Received return value {res} from update.")

    def validate_procedures(self, procedures: List[MutableMapping]) -> None:
        """ Given all the procedures the component is involved in, checks them. """
        # skip validation if no procedure is given
        if not procedures:
            warnings.warn(
                f"{self} is an active component but was not used in this protocol."
                " If this is intentional, ignore this warning."
            )
            return

        # check for conflicting continuous procedures
        procedures_without_time = [
            x for x in procedures if x["start"] is None and x["stop"] is None
        ]
        if len(procedures_without_time) > 1:
            raise RuntimeError(
                f"{self} cannot have two procedures for the entire duration of the protocol. "
                "If each procedure defines a different attribute to be set for the entire duration, "
                "combine them into one call to add(). Otherwise, reduce ambiguity by defining start "
                "and stop times for each procedure. "
            )

        # Unlike mw, avoid inferring stop time for procedures.
        # Procedures will become atomic in XDL steps,
        # avoiding multiple procedures per component per step.
        for procedure in procedures:
            assert procedure["start"] is not None
            assert procedure["stop"] is not None

        # For now we still have to check for conflicting procedures
        for i, procedure in enumerate(procedures):
            try:
                # the start time of the next procedure
                next_start = procedures[i + 1]["start"]
            except IndexError:  # Last one
                continue

            # check for overlapping procedures
            if next_start < procedure["stop"] and not math.isclose(
                next_start, procedure["stop"]
            ):
                msg = "Cannot have two overlapping procedures. "
                msg += f"{procedure} and {procedures[i + 1]} conflict"
                raise RuntimeError(msg)
