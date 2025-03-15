from flowchem.utils.people import samuel_saraiva
from .el_flow import EPC, MFC
from loguru import logger


class VirtualPropar:

    id = 0

    setpoint = 0

    measure = 0


class VirtualEPC(EPC):

    def __init__(
            self,
            port: str,
            name="",
            channel: int = 1,
            address: int = 0x80,
            max_pressure: float = 10,  # bar = 100 % = 32000
    ) -> None:

        try:
            super().__init__(port, name, channel, address, max_pressure)
        except OSError as e:
            self.device_info.authors = [samuel_saraiva]
            self.device_info.manufacturer = "VirtualBronkhorst"
            self.el_press = VirtualPropar()
            self.id = self.el_press.id
            logger.debug(f"Connected virtual EPC {self.id} to {self.port}")


class VirtualMFC(MFC):

    def __init__(
            self,
            port: str,
            name="",
            channel: int = 1,
            address: int = 0x80,
            max_flow: float = 9,  # ml / min = 100 % = 32000
    ) -> None:

        try:
            super().__init__(port, name, channel, address, max_flow)
        except OSError as e:
            # Metadata
            self.device_info.authors = [samuel_saraiva]
            self.device_info.manufacturer = "VirtualBronkhorst"
            self.el_flow = VirtualPropar()
            self.id = self.el_flow.id
            logger.debug(f"Connected virtual EPC {self.id} to {self.port}")



