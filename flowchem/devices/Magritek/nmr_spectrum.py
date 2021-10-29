""" NMR-spectrum object represents an NMR spectrum.  """
import nmrglue as ng
from pathlib import Path
import matplotlib.pyplot as plt


class NMR_Spectrum:
    """ General spectrum object, instantiated from Spinsolve folder w/ experimental results. """

    def __init__(self, location: Path):
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
        """ Basic spectrum processing. Application-specific processing suggested. """
        # Zerofill
        self.processed_data = ng.proc_base.zf_auto(
            ng.proc_base.zf_double(self.raw_data, 1)
        )

        # FT
        self.processed_data = ng.proc_base.fft(self.processed_data)

        # Autophase
        self.processed_data = ng.proc_autophase.autops(
            self.processed_data, "acme", disp=False
        )

        # Delete imaginary
        self.processed_data = ng.proc_base.di(self.processed_data)

    def plot(self, ppm_range=(8, 0)):
        """ Returns spectrum as matplotlib figure """
        if self.processed_data is None:
            self.process()

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.uc.ppm_scale(), self.processed_data)
        plt.xlim(ppm_range)  # plot as we are used to, from positive to negative
        return fig
