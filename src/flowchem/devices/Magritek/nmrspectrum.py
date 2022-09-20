""" NMR-spectrum object represents an NMR spectrum.  """
import time
from pathlib import Path

import nmrglue as ng

try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ModuleNotFoundError:
    HAS_MATPLOTLIB = False


class NMRSpectrum:
    """General spectrum object, instantiated from Spinsolve folder w/ experimental results."""

    def __init__(self, location: Path):
        jcamp_file = location / "nmr_fid.dx"
        if not jcamp_file.exists():
            print("File nmr_fid.dx not existing, waiting 2 sec just in case...")
            time.sleep(2)
        self.dic, self.raw_data = ng.spinsolve.read(dir=location.as_posix())
        self.processed_data = None

    @property
    def uc(self):
        """

        Returns:

        """
        data = self.processed_data if self.processed_data is not None else self.raw_data
        return ng.spinsolve.make_uc(self.dic, data)

    def process(self):
        """Basic spectrum processing. Application-specific processing suggested."""
        # Zerofill
        self.processed_data = ng.proc_base.zf_auto(
            ng.proc_base.zf_double(self.raw_data, 1)
        )

        # FT
        self.processed_data = ng.proc_base.fft(self.processed_data)

        # Phasing
        try:
            # Try to extract phase info from JCAMP-DX file...
            ph0 = float(self.dic["dx"]["$PHC0"].pop())
            ph1 = float(self.dic["dx"]["$PHC1"].pop())
            self.processed_data = ng.proc_base.ps(self.processed_data, ph0, ph1, True)
        except KeyError:
            # Auto phase needed - no info on phase from nmrglue
            self.processed_data = ng.proc_autophase.autops(
                self.processed_data,
                "acme",
                disp=False,
            )

        # Delete imaginary
        self.processed_data = ng.proc_base.di(self.processed_data)

    def plot(self, ppm_range=(8, 0)):
        """Returns spectrum as matplotlib figure"""
        if not HAS_MATPLOTLIB:
            raise RuntimeError("Plot function requested but matplotlib not installed!")

        if self.processed_data is None:
            self.process()

        fig = plt.figure()
        axes = fig.add_subplot(111)
        axes.plot(self.uc.ppm_scale(), self.processed_data)

        plt.xlim(ppm_range)  # plot as we are used to, from positive to negative
        return fig
