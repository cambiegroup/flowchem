""" Test FlowIR, needs actual connection to the device :( """
import asyncio
import datetime
import sys

import pytest

from flowchem.devices.MettlerToledo.iCIR_common import IRSpectrum
from flowchem import FlowIR


def check_pytest_asyncio_installed():
    """ Utility function for pytest plugin """
    import os
    from importlib import util
    if not util.find_spec("pytest_asyncio"):
        print("You need to install pytest-asyncio first!", file=sys.stderr)
        sys.exit(os.EX_SOFTWARE)


@pytest.fixture()
async def flowir():
    """ Return local FlowIR object """
    return FlowIR(FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS.replace("localhost", "BSMC-YMEF002121"))


@pytest.mark.asyncio
@pytest.mark.FlowIR
async def test_connected(flowir):
    async with flowir as spectrometer:
        assert await spectrometer.is_iCIR_connected()


@pytest.mark.asyncio
@pytest.mark.FlowIR
async def test_probe_info(flowir):
    async with flowir as spectrometer:
        info = await spectrometer.probe_info()
        assert all(field in info for field in ("spectrometer", "spectrometer_SN", "probe_SN", "detector"))


@pytest.mark.asyncio
@pytest.mark.FlowIR
async def test_probe_status(flowir):
    async with flowir as spectrometer:
        status = await spectrometer.probe_status()
        assert status == "Not running"


@pytest.mark.asyncio
@pytest.mark.FlowIR
async def test_is_running(flowir):
    async with flowir as spectrometer:
        # Check idle
        assert await spectrometer.is_running() is False

        # Make busy
        template_name = "15_sec_integration.iCIRTemplate"
        await spectrometer.start_experiment(template=template_name)

        # Check busy
        assert await spectrometer.is_running() is True

        # Restore idle
        await spectrometer.stop_experiment()
        await spectrometer.wait_until_idle()


@pytest.mark.asyncio
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


@pytest.mark.asyncio
@pytest.mark.FlowIR
async def test_spectra(flowir):
    # This implies the previous test run successfully, thus last spectrum is now
    async with flowir as spectrometer:
        last_raw = await spectrometer.last_spectrum_raw()
        assert isinstance(last_raw, IRSpectrum)

        last_bg = await spectrometer.last_spectrum_background()
        assert isinstance(last_bg, IRSpectrum)
