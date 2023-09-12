"""Distribution valves, generally connected to syringe pumps, direct the flow from a fixed port to one of the others."""
from flowchem.components.valves.valve import Valve
from flowchem.devices.flowchem_device import FlowchemDevice


class TwoPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        positions = {
            "1": [("pump", "1")],
            "2": [("pump", "2")],
        }
        super().__init__(name, hw_device, positions, ports=["pump", "1", "2"])


class SixPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        positions = {
            "1": [("pump", "1")],
            "2": [("pump", "2")],
            "3": [("pump", "3")],
            "4": [("pump", "4")],
            "5": [("pump", "5")],
            "6": [("pump", "6")],
        }
        super().__init__(
            name,
            hw_device,
            positions,
            ports=["pump", "1", "2", "3", "4", "5", "6"],
        )


class TwelvePortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        positions = {
            "1": [("pump", "1")],
            "2": [("pump", "2")],
            "3": [("pump", "3")],
            "4": [("pump", "4")],
            "5": [("pump", "5")],
            "6": [("pump", "6")],
            "7": [("pump", "7")],
            "8": [("pump", "8")],
            "9": [("pump", "9")],
            "10": [("pump", "10")],
            "11": [("pump", "11")],
            "12": [("pump", "12")],
        }
        super().__init__(
            name,
            hw_device,
            positions,
            ports=[
                "pump",
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "12",
            ],
        )


class SixteenPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        positions = {
            "1": [("pump", "1")],
            "2": [("pump", "2")],
            "3": [("pump", "3")],
            "4": [("pump", "4")],
            "5": [("pump", "5")],
            "6": [("pump", "6")],
            "7": [("pump", "7")],
            "8": [("pump", "8")],
            "9": [("pump", "9")],
            "10": [("pump", "10")],
            "11": [("pump", "11")],
            "12": [("pump", "12")],
            "13": [("pump", "13")],
            "14": [("pump", "14")],
            "15": [("pump", "15")],
            "16": [("pump", "16")],
        }
        super().__init__(
            name,
            hw_device,
            positions,
            ports=[
                "pump",
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "12",
                "13",
                "14",
                "15",
                "16",
            ],
        )
