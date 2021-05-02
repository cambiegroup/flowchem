import numpy as np
import pandas as pd


class Spectrum:
    def __init__(self, x, y):
        assert len(x) == len(y)
        self._x = np.array(x)
        self._y = np.array(y)

    @property
    def empty(self):
        return self._y.size == 0

    def as_df(self) -> pd.core.frame.DataFrame:
        pd.DataFrame(self._x, self._y)

    def __str__(self):
        return f"Spectrum object [" \
               f"X: min={min(self._x):.2f}, max={max(self._x):.2f}, len={len(self._x)}," \
               f"Y: min={min(self._y):.2f}, max={max(self._y):.2f}, len={len(self._y)}]"


class IRSpectrum(Spectrum):
    def __init__(self, wavenumber, intensity):
        super().__init__(wavenumber, intensity)
