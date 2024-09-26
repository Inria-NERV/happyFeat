import numpy as np
import xarray as xr
from timeflux.core.node import Node

class SelectRange(Node):
    """Select a subset of the given data along the space and frequency dimensions.

    Attributes:
        i (Port): default data input, expects DataArray.
        o (Port): default output, provides DataArray.

    Args:
         selections (list of tuples): List of tuples where each tuple contains a space identifier and a frequency range.
         inclusive (bool): Whether the boundaries are inclusive or exclusive. Default: `False`.

    Example:

        In this example, we have an input DataArray with dimensions 'time', 'frequency', and 'space'. We want to select
        data for specific spaces with corresponding frequency ranges. The list of tuples specifies the space and frequency range:

        * ``selections`` = `[("space1", [8, 12]), ("space2", [10, 14])]`
        * ``inclusive`` = `True`

        If the data received on port ``i`` is: ::

            <xarray.DataArray (time: 3, frequency: 4, space: 2)>
            array([[[0.1, 0.2],
                    [0.3, 0.4],
                    [0.5, 0.6],
                    [0.7, 0.8]]])
            Coordinates:
              * time       (time) datetime64[ns] 2023-01-01T00:00:00 ...
              * frequency  (frequency) float64 8.0 10.0 12.0 14.0
              * space      (space) <U6 'space1' 'space2'

        The data provided on port ``o`` will be: ::

            <xarray.DataArray (time: 3, frequency: 2, space: 2)>
            array([[[0.3, 0.2],
                    [0.5, 0.4]]])
            Coordinates:
              * time       (time) datetime64[ns] 2023-01-01T00:00:00 ...
              * frequency  (frequency) float64 10.0 12.0
              * space      (space) <U6 'space1' 'space2'

    """

    def __init__(self, selections, inclusive=False):
        self._selections = selections  # list of tuples (space, frequency range)
        self._inclusive = inclusive    # include boundaries.

    def update(self):
        if not self.i.ready():
            return

        data = self.i.data
        selected_data = []

        for space, (freq_min, freq_max) in self._selections:
            # Mask for the current space
            mask_space = data['space'] == space
            
            # Mask for the current frequency range
            if self._inclusive:
                mask_frequency = (data['frequency'] >= freq_min) & (data['frequency'] <= freq_max)
            else:
                mask_frequency = (data['frequency'] > freq_min) & (data['frequency'] < freq_max)
            
            # Apply masks to select the subset of data
            selected_subset = data.sel(space=space).where(mask_frequency, drop=True)
            selected_data.append(selected_subset)

        # Combine the selected data
        if selected_data:
            combined_data = xr.concat(selected_data, dim='frequency')
            self.o.data = combined_data
            self.o.meta = self.i.meta
        else:
            self.o.data = xr.DataArray()
            self.o.meta = {}
