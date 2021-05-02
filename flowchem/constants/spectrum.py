import numpy as np
import pandas as pd
from scipy import integrate


class Spectrum:
    def __init__(self, x, y):
        assert len(x) == len(y)
        self._x = np.array(x)
        self._y = np.array(y)

    @property
    def empty(self):
        return self._y.size == 0

    def integrate(self, x_start: float, x_end: float) -> float:
        """ Integrates dy/dx with trapezoid rule """
        integration_interval = self.as_df().query(f"{x_start} <= index <= {x_end}")[0]
        return integrate.trapezoid(integration_interval.values, integration_interval.index.to_numpy())

    def as_df(self) -> pd.DataFrame:
        """ Returns spectrum as pd.DataFrame """
        return pd.DataFrame(data=self._y, index=self._x)

    def __str__(self):
        return f"Spectrum object [" \
               f"X: min={min(self._x):.2f}, max={max(self._x):.2f}, len={len(self._x)}," \
               f"Y: min={min(self._y):.2f}, max={max(self._y):.2f}, len={len(self._y)}]"


class IRSpectrum(Spectrum):
    """
    IR spectrum class.
    Consider rampy for advance features (baseline fit, etc)
    See e.g. https://github.com/charlesll/rampy/blob/master/examples/baseline_fit.ipynb
    """
    def __init__(self, wavenumber, intensity):
        super().__init__(wavenumber, intensity)


if __name__ == '__main__':
    pass