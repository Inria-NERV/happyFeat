import numpy as np
import pandas as pd
import xarray as xr
from scipy.signal import welch
from scipy.fft import fftfreq, rfftfreq, fft, rfft
import numpy as np
import pandas as pd
import xarray as xr
from timeflux.core.node import Node

class NewBands(Node):
    """Averages the XArray values over freq dimension according to the frequencies bands given in arguments.

    This node selects a subset of values over the chosen dimensions, averages them along this axis and convert the result into a flat dataframe.
    This node will output as many ports bands as given bands, with their respective name as suffix.

        Attributes:
            i (Port): default output, provides DataArray with 3 dimensions (time, freq, space).
            o (Port): Default output, provides DataFrame.

    """

    def __init__(self, bands=None, relative=False):

        """
        Args:
           bands (dict): Define the band to extract given its name and its range.
                         An output port will be created with the given names as suffix.

        """
        bands = bands or {
            "delta": [1, 4],
            "theta": [4, 8],
            "alpha": [8, 12],
            "beta": [12, 30],
        }
        self._relative = relative
        self._bands = []
        for band_name, band_range in bands.items():
            self._bands.append(
                dict(
                    name=band_name,
                    slice=slice(band_range[0], band_range[1]),
                    meta={"bands": {"range": band_range, "relative": relative}},
                )
            )

    def update(self):

        # When we have not received data, there is nothing to do
        if not self.i.ready():
            return

        # Initialize an empty DataFrame to hold all bands
        all_bands_df = pd.DataFrame()

        # At this point, we are sure that we have some data to process
        for band in self._bands:
            # 1. select the Xarray on freq axis in the range, 2. sum along freq axis
            band_power = (
                self.i.data.loc[{"frequency": band["slice"]}].sum("frequency").values
            )
            if self._relative:
                tot_power = self.i.data.sum("frequency").values
                tot_power[tot_power == 0.0] = 1
                band_power /= tot_power

            # Create DataFrame for this band
            band_df = pd.DataFrame(
                columns=[f"{band['name']}_{col}" for col in self.i.data.space.values],
                index=self.i.data.time.values,
                data=band_power,
            )

            # Concatenate with the main DataFrame
            all_bands_df = pd.concat([all_bands_df, band_df], axis=1)

        # Assign the DataFrame to the output port
        self.o.data = all_bands_df
        self.o.meta = self.i.meta