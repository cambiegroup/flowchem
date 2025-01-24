"""Base Autosampler meta component."""
from loguru import logger

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.meta_components.gantry3D import gantry3D
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.distribution_valves import (
    TwoPortDistributionValve,
    FourPortDistributionValve,
    SixPortDistributionValve,
    TwelvePortDistributionValve,
    SixteenPortDistributionValve,
    )
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve
from flowchem.devices.flowchem_device import FlowchemDevice


class Autosampler(FlowchemComponent):
    """
    A CNC device that controls movement in 3 dimensions (X, Y, Z).
    Each axis can operate in discrete or continuous mode.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice, _config: dict) -> None:
        """
        Initialize the Autosampler component with individual components.

        Args:
            name (str): Name of the CNC device.
            hw_device (FlowchemDevice): Hardware device interface.
            axes_config (dict): Configuration for each axis. Example:
                _config = {
                    "tray_config": {
                        "rows": [1, 2, 3, 4, 5, 6, 7, 8],
                        "columns": ["a", "b", "c", "d", "e", "f"]
                    },
                    "needle_positions": ["WASH", "WASTE", "EXCHANGE", "TRANSPORT"],
                    "syringe_valve": {"mapping": {0: "NEEDLE", 1: "WASH",  2: "WASH_PORT2", 3: "WASTE"},
                }
        """
        super().__init__(name, hw_device)
        self._config = _config

        #gantry3D
        self.add_api_route("/needle_position", self.set_needle_position, methods=["PUT"])
        self.add_api_route("/needle_position", self.set_xy_position, methods=["PUT"])
        self.add_api_route("/needle_position", self.set_z_position, methods=["PUT"])
        self.add_api_route("/needle_position", self.connect_to_position, methods=["PUT"])
        self.add_api_route("/is_needle_running", self.is_needle_running, methods=["GET"])
        #Pump
        self.add_api_route("/infuse", self.infuse, methods=["PUT"])
        self.add_api_route("/withdraw", self.withdraw, methods=["PUT"])
        self.add_api_route("/is_pumping", self.is_pumping, methods=["GET"])
        #Syringe Valve
        self.add_api_route("/syringe_valve_position", self.set_syringe_valve_position, methods=["PUT"])
        self.add_api_route("/syringe_valve_position", self.get_syringe_valve_position, methods=["GET"])
        #Injection Valve
        self.add_api_route("/injection_valve_position", self.set_injection_valve_position, methods=["PUT"])
        self.add_api_route("/injection_valve_position", self.get_injection_valve_position, methods=["GET"])
        #Meta Methods
        self.add_api_route("/wash_needle", self.wash_needle, methods=["PUT"])

        # valve_class_map = {
        #     "FourPortDistributionValve": FourPortDistributionValve,
        #     "SixPortDistributionValve": SixPortDistributionValve,
        # }
        {"axes_config": {
                "x": {"mode": "discrete", "positions": _config["tray_config"]["rows"]},
                "y": {"mode": "discrete", "positions": _config["tray_config"]["columns"]},
                "z": {"mode": "discrete", "positions": ["UP", "DOWN"]}
            }
        }

        # Check config #
        #Syringe valve mapping
        required_syringe_valve_values = {"NEEDLE", "WASH", "WASTE"}  # Set of required values
        syringe_mapping = config.get("syringe_valve", {}).get("mapping", {})
        updated_mapping = {key: value.upper() for key, value in syringe_mapping.items()}
        missing_values = required_syringe_valve_values - set(updated_mapping.values())  # Check if required values are in the mapping
        if missing_values:
            logger.error(f"Missing required values in syringe valve mapping: {missing_values}")
        config["syringe_valve"]["mapping"] = updated_mapping
        #Needle positions
        required_needle_positions = {"WASH", "WASTE"}
        needle_positions = config.get("needle_positions", [])
        updated_needle_positions = [pos.upper() for pos in needle_positions]
        missing_needle_positions = required_needle_positions - set(updated_needle_positions)
        if missing_needle_positions:
            logger.error(f"Missing required needle positions: {missing_needle_positions}")
        config["needle_positions"] = updated_needle_positions


        self.gantry3D = gantry3D(
            f"{name}_gantry3D",
            hw_device,
            axes_config=_config["axes_config"],
        )
        self.pump = SyringePump(
            f"{name}_pump",
            hw_device,
        )
        # valve_type = _config["syringe_valve"]["type"]
        # if valve_type not in valve_class_map:
        #     logger.error(
        #         f"Invalid syringe_valve_type: {valve_type}. "
        #         f"Must be one of {list(valve_class_map.keys())}."
        #     )
        #ToDo: Is the syringe valve always four ports?
        self.syringe_valve = FourPortDistributionValve(
            f"{name}_syringe_valve",
            hw_device,
        )
        self.syringe_valve.identifier = "syringe_valve"
        self.syringe_valve.mapping = _config["syringe_valve"]["mapping"]

        self.injection_valve = SixPortTwoPositionValve(
                f"{name}_injection_valve",
                hw_device,
            )
        self.injection_valve.identifier = "injection_valve"
        self.injection_valve.mapping = {0: 'LOAD', 1: 'INJECT'}

    # Gantry3D Methods
    async def set_needle_position(self, position: str = "") -> None:
        """
        Move the needle to one of the predefined positions.
        """
        if position not in self._config["needle_positions"]:
            logger.error(
                f"Invalid needle position: '{position}'. "
                f"Must be one of {self._config['needle_positions']}."
            )

    # async def get_needle_position(self) -> dict:
    #     """
    #     Get.
    #     """
    #     pos = await self.gantry3D.get_position()
    #     return pos

    async def set_xy_position(self, x: int | float | str = 0, y: int | float | str = 0) -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate.
        """
        await self.gantry3D.set_x_position(position=x)
        await self.gantry3D.set_y_position(position=y)
    # Necessary to return values? Maybe just call super().set_xy_position() to run checks before the actual set_xy_position() from the autosampler.

    async def set_z_position(self, z: int | float | str = 0) -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate.
        """
        await self.gantry3D.set_z_position(position=z)

    # Pump Methods
    async def infuse(self, rate: str = None, volume: str = None) -> bool:
        """
        Dispense with syringe.
        Args:
            volume: volume to dispense in mL

        Returns: None
        """
        await self.pump.infuse(rate=rate, volume=volume)

    async def withdraw(self, rate: str = None, volume: str = None) -> bool:  # type: ignore
        """
        Aspirate with built in syringe.
        Args:
            volume: volume to aspirate in mL

        Returns: None
        """
        await self.pump.withdraw(rate=rate, volume=volume)

    # Syringe valve Methods
    async def set_syringe_valve_position(self, position: str = None):
        """Set the position of the syringe valve.        """
        await self.syringe_valve.set_position(position=position)

    async def get_syringe_valve_position(self, position: str = None):
        """Retrieve the current position of the syringe valve."""
        await self.syringe_valve.get_position(position=position)

    # Injection valve Methods
    async def set_injection_valve_position(self, position: str | tuple = ""):
        """Set the position of the injection valve."""
        await self.injection_valve.set_position(position=position)

    async def get_injection_valve_position(self):
        """Retrieve the current position of the injection valve."""
        await self.injection_valve.get_position()


    # AS Methods

