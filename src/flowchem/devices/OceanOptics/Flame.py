"""
the flame is using usb and  libusb

    1. pip install pyusb
    2. pip install libusb
    3. libusb-1.0.dll will be automatically added to:

    \venv\Lib\site-packages\libusb\_platform\_windows\x64

    \venv\Lib\site-packages\libusb\_platform\_windows\x32

    Now just add those paths (the full path) to Windows Path and restart CMD / PyCharm.
    ref. https://stackoverflow.com/questions/13773132/pyusb-on-windows-no-backend-available#comment135836462_77052975

for more information of seabreeze-python
https://github.com/ap--/python-seabreeze/tree/main?tab=readme-ov-file
"""

import seabreeze
# use the pyseabreeze backend (pyusb)
seabreeze.use("pyseabreeze")

from seabreeze.spectrometers import Spectrometer

from loguru import logger
import asyncio


from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import wei_hsin

class FlameOptical(FlowchemDevice):

    def __int__(self, name="", serial_number: str | None = None):
        self.serial_n = serial_number
        # self.idVendor = 0x2457
        # self.idProduct = 0x1022
        super().__init__(name)

        # Metadata
        self.device_info.authors = [wei_hsin]
        self.device_info.manufacturer = "OceanOptics"
        self.device_info.package = "python-seabreeze"

        # use the
        if self.serial_n is None:
            self.spectrometer = Spectrometer.from_first_available()
        else:
            self.spectrometer = Spectrometer.from_serial_number(self.serial_n)

        self.model: str = self.spectrometer.model  # USB4000  #todo: list all model??
        self.max_intensity: float = self.spectrometer.max_intensity  # 65535.0 in (a.u.)
        self.pixels: int = self.spectrometer.pixels  # 3840

        # min and max integration time in micro seconds
        self.integration_time_micros_limits: tuple = self.spectrometer.integration_time_micros_limits

        self.wavelengths = self.spectrometer.wavelengths()  # numpy.ndarray (3840,) in (nm)

        # Note: the pump requires "\n\r" as EOL, the valves "\r\n"! So this is set by the subclasses
        self.eol = b""

        # Lock communication between write and read reply
        self._lock = asyncio.Lock()

    async def initialize(self):
        pass

    async def power_on(self):
        # open the connection to SeaBreezeDevice
        self.spectrometer.open()

    async def power_off(self):
        # close the connection to SeaBreezeDevice
        self.spectrometer.close()

    async def get_spectrum(self):
        return self.spectrometer.spectrum()

    async def get_intensity(self):
        return self.spectrometer.intensities()

    async def get_wavelength(self):
        return self.wavelengths

def all_usb_devices_by_usb():
    import usb
    from usb import backend

    # find all usb devices
    # next(Path(libusb.__file__).parent.rglob('x64/libusb-1.0.dll'))
    # backend = usb.backend.libusb1.get_backend(find_library=lambda x: r"'C:/Users/BS-Flowlab/PycharmProjects/flowchem/venv/lib/site-packages/libusb/_platform/_windows/x64/libusb-1.0.dll'")  # adapt to your path
    # usb_devices = usb.core.find(backend=backend, find_all=True)
    # usb_devices = usb.core.find(find_all=True)
    # for usb_device in usb_devices:
    #     print(usb_device)

    # find our device
    dev = usb.core.find(idVendor=0x2457, idProduct=0x1022)
    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    dev.set_configuration()

    # get an endpoint instance
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    ep1, ep2, ep3, ep4 = intf.endpoints()
    assert [ep1, ep2, ep3, ep4] is not None

    # ep1 = usb.util.find_descriptor(
    #     intf,
    #     # match the first OUT endpoint
    #     custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    #
    # ep_spc = usb.util.find_descriptor(
    #     intf,
    #     # match the first IN endpoint
    #     custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

async def main():
    flame = FlameOptical()
    await flame.power_off()

if __name__ == "__main__":
    # all_usb_devices_by_usb()
    asyncio.run(main())