import numpy as np
import pandas as pd
import xarray as xr
import os
import sys
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError

def load_csv_np(file):
    """
    Load data from CSV file using numpy.

    Parameters
    ----------
    file : string
        Path to the CSV file.

    Returns
    -------
    header : array
        The header row of the CSV file.
    data : array
        The numerical data in the CSV file, excluding the last three columns.
    """
    header = np.loadtxt(file, dtype=str, delimiter=',', max_rows=1)
    nbcols = header.size - 3
    data = np.loadtxt(file, dtype=float, delimiter=',', skiprows=1, usecols=list(range(2,nbcols)))
    return header, data

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
                header, data = load_csv_np(self.filename)
                # Extract time column index and data
                time_col_index = 0  # The index of the time column in the data
                time = pd.to_datetime(data[:, time_col_index], unit='s', errors='coerce')
                
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
                parts = base.split('-')
                label = parts[-1] 
                label_array = np.array([label] * n_samples,dtype=object)
                # Assign the DataArray to the output port
                getattr(self, "o").data = data_array
                getattr(self,"o").meta = {'label':label_array}

            except IOError as e:
                raise WorkerInterrupt(e)

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
