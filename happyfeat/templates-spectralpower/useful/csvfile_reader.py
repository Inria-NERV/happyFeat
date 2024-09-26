import numpy as np
import pandas as pd
import xarray as xr
import os
import sys
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError

def load_csv_np(file):
    # Read header separately
    header = np.loadtxt(file, dtype=str, delimiter=',', max_rows=1)
    nbcols = header.size - 3  # We discard 'End Time', 'Event Id', 'Event Date', 'Event Duration'

    # Load 'Time' column as strings
    time_data = np.loadtxt(file, dtype=str, delimiter=',', skiprows=1, usecols=[0])

    # Load remaining columns as floats, except the 'End Time' and the last three columns
    data = np.loadtxt(file, dtype=float, delimiter=',', skiprows=1, usecols=list(range(2, nbcols)))

    return header, time_data, data

class ReadFromCSV(Node):
    """Read from CSV files and transform to initial DataFrame."""

    def __init__(self, filename):
        """
        Initialize.

        Parameters
        ----------
        filename : string
            The name of the CSV file to read.
        """
        # Load store
        self.filename = self._find_path(filename)
        self.counter = 0

    def update(self):
        """
        Read the CSV file and transform it to the initial xarray format.

        Returns
        -------
        xarray.DataArray
            The transformed DataArray.
        """
        self.counter += 1
        if self.counter == 1:
            try:
                header, time_data, data = load_csv_np(self.filename)
            except IOError as e:
                raise WorkerInterrupt(e)

            if data.size > 0:

                # Ensure 'Time' is in datetime format
                time = pd.to_datetime(time_data).tz_localize(None)

                # Extract space and frequency information
                freq_space = header[2:-3]
                
                freq = np.unique([float(col.split(':')[-1]) for col in freq_space])
                space = np.unique([col.split(':')[0] for col in freq_space])
                # Calculate the required shape
                n_samples = len(time)
                n_freq = len(freq)
                n_space = len(space)
                # Reshape data to the desired format
                reshaped_data = data.reshape((n_samples, n_freq, n_space))

                # Create the DataArray
                data_array = xr.DataArray(
                    reshaped_data,
                    coords={
                        'time': ('time', time.astype('datetime64[ns]')),
                        'frequency': ('frequency', freq.astype('float64')),
                        'space': ('space', space.astype('object'))
                    },
                    dims=["time", "frequency", "space"]
                )
                # Extract label from filename
                base, ext = os.path.splitext(self.filename)
                label = base[-1]
                label_array = np.array([label] * n_samples,dtype=object)
                # Assign the DataArray to the output port
                getattr(self, "o").data = data_array
                getattr(self,"o").meta = {'label':label_array}

    def _find_path(self, path):
        path = os.path.normpath(path)
        if os.path.isabs(path):
            if os.path.isfile(path):
                return path
        else:
            for base in sys.path:
                full_path = os.path.join(base, path)
                if os.path.isfile(full_path):
                    return full_path
        raise WorkerLoadError(f"File `{path}` could not be found in the search path.")
