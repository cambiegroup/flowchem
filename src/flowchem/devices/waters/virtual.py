from flowchem.utils.people import samuel_saraiva
from .waters_ms import WatersMS
from loguru import logger


class VirtualWatersMS(WatersMS):

    def __init__(self, name, **kwargs) -> None:

        super().__init__(name, **kwargs)

        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer = "Virtual Clarity"
        self.device_info.model = "Virtual"

    async def record_mass_spec(self, sample_name: str,
                               run_duration: int = 0,
                               queue_name = "next.txt",
                               do_conversion: bool = False,
                               output_dir="W:\BS-FlowChemistry\data\open_format_ms"):
        logger.info("Recording fake mass spectrum!")

