import numpy as np
import pandas as pd
from scipy import integrate


class Spectrum:
    """ Generic dimensional spectrum representation. """
    def __init__(self, x, y):
        assert len(x) == len(y)
        self._x = np.array(x)
        self._y = np.array(y)

    @property
    def empty(self) -> True:
        """ True if there are no data """
        return self._y.size == 0

    def integrate(self, x_start: float, x_end: float) -> float:
        """ Integrates dy/dx with trapezoid rule """
        integration_interval = self.as_df().query(f"{x_start} <= index <= {x_end}")[0]
        # Index sorting prevent negative integrals in IR spectra
        integration_interval.sort_index(inplace=True)
        return integrate.trapezoid(
            integration_interval.values, integration_interval.index.to_numpy()
        )

    def as_df(self) -> pd.DataFrame:
        """ Returns spectrum as pd.DataFrame """
        return pd.DataFrame(data=self._y, index=self._x)

    def __str__(self):
        return (
            f"Spectrum object ["
            f"X: min={min(self._x):.2f}, max={max(self._x):.2f}, len={len(self._x)},"
            f"Y: min={min(self._y):.2f}, max={max(self._y):.2f}, len={len(self._y)}]"
        )


if __name__ == "__main__":
    pass
