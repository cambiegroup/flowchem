"""Test FlowIR, needs actual connection to the device :(."""
import asyncio
import datetime

import pytest

from flowchem.components.analytics.ir import IRSpectrum
from flowchem.devices.mettlertoledo.icir import IcIR


@pytest.fixture
def spectrometer() -> IcIR:
    """Workaround for https://youtrack.jetbrains.com/issue/PY-30279/"""


@pytest.fixture()
async def spectrometer() -> IcIR:  # noqa
    """Return local FlowIR object."""
    s = IcIR(
        template="template",
        url=IcIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS.replace(
            "localhost",
            "BSMC-YMEF002121",
        ),
    )
    await s.initialize()
    return s


@pytest.mark.FlowIR()
async def test_connected(spectrometer):
    assert await spectrometer.is_iCIR_connected()


@pytest.mark.FlowIR
async def test_probe_info(spectrometer):
    info = await spectrometer.probe_info()
    assert all(
        field in info
        for field in ("spectrometer", "spectrometer_SN", "probe_SN", "detector")
    )


@pytest.mark.FlowIR
async def test_probe_status(flowir):
    async with flowir as spectrometer:
        status = await spectrometer.probe_status()
        assert status == "Not running"


@pytest.mark.FlowIR
async def test_spectrum_acquisition(flowir):
    async with flowir as spectrometer:
        template_name = "15_sec_integration.iCIRTemplate"
        await spectrometer.start_experiment(template=template_name)

        # Wait for a spectrum
        spectrum = await spectrometer.last_spectrum_treated()
        while spectrum.empty:
            spectrum = await spectrometer.last_spectrum_treated()

        assert isinstance(spectrum, IRSpectrum)

        spectra_count = await spectrometer.sample_count()

        while await spectrometer.sample_count() == spectra_count:
            await asyncio.sleep(1)

        # sample_count() increments as expected
        assert await spectrometer.sample_count() == spectra_count + 1

        # Check date
        date = await spectrometer.last_sample_time()
        assert isinstance(date, datetime.datetime)
        assert date.date() == datetime.date.today()

        # Restore idle
        await spectrometer.stop_experiment()
        await spectrometer.wait_until_idle()


@pytest.mark.FlowIR
async def test_spectra(flowir):
    # This implies the previous test run successfully, thus last spectrum is now
    async with flowir as spectrometer:
        last_raw = await spectrometer.last_spectrum_raw()
        assert isinstance(last_raw, IRSpectrum)

        last_bg = await spectrometer.last_spectrum_background()
        assert isinstance(last_bg, IRSpectrum)
