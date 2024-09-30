import numpy as np
import xarray as xr
from timeflux.core.node import Node

class SelectFrequency(Node):
    """Select data for given space identifiers at the closest available frequency that is 
    less than or equal to the specified target frequency.

    Attributes:
        i (Port): default data input, expects DataArray.
        o (Port): default output, provides DataArray.

    Args:
        selections (list of tuples): List of tuples where each tuple contains a space identifier and a target frequency.

    Example:

        In this example, we have an input DataArray with dimensions 'time', 'frequency', and 'space'. We want to select
        data for specific spaces at the closest available frequency to the specified target frequency:

        * ``selections`` = `[("space1", 12.5), ("space2", 14.0)]`

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
            array([[[0.5, 0.8]]])
            Coordinates:
              * time       (time) datetime64[ns] 2023-01-01T00:00:00 ...
              * frequency  (frequency) float64 12.0 14.0
              * space      (space) <U6 'space1' 'space2'
    """

    def __init__(self, selections):
        self._selections = selections  # list of tuples (space, target frequency)

    def update(self):
        if not self.i.ready():
            return

        data = self.i.data
        selected_data = []
        # Retrieve available spaces and frequencies from the data
        available_spaces = data['space'].values

        for space, target_frequency in self._selections:
            # Check if the space exists
            if space not in available_spaces:
                raise ValueError(f"Space '{space}' not found in the data.")
            # Select data for the current space
            space_data = data.sel(space=space)
            
            # Retrieve the available frequencies
            available_frequencies = space_data['frequency'].values
            
            # Filter frequencies less than or equal to the target frequency
            valid_frequencies = available_frequencies[available_frequencies <= target_frequency]
            
            # If there are valid frequencies, find the closest one
            if len(valid_frequencies) > 0:
                closest_frequency = valid_frequencies.max()
            else:
                # If no valid frequency, find the closest available frequency (below or above)
                closest_frequency = available_frequencies[np.abs(available_frequencies - target_frequency).argmin()]
            
            #check if the frequency range is valid
            if closest_frequency is None:
                raise ValueError(f"frequency '{target_frequency}' is out of range")
            # Select the data for the closest frequency
            selected_subset = space_data.sel(frequency=closest_frequency)
            selected_data.append(selected_subset)

        # Combine the selected data along the 'space' dimension
        if selected_data:
            combined_data = xr.concat(selected_data, dim='space')

            # Transpose the data to have dimensions (time, space)
            combined_data = combined_data.transpose('time', 'space')
            self.o.data = combined_data
            self.o.meta = self.i.meta
        else:
            self.o.data = xr.DataArray()
            self.o.meta = {}
