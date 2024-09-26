"""timeflux.nodes.csv: CSV nodes"""

import pandas as pd
import os
import time
from timeflux.core.node import Node
import xarray as xr
from timeflux.core.exceptions import ValidationError, WorkerInterrupt
import numpy as np





class SaveToCSV(Node):
    """Save to CSV files."""

    def __init__(self, filename=None, path="/tmp", index_dim="time", rate=500):
        """
        Initialize.

        Parameters
        ----------
        filename: string
            Base name of the file (without extension). If not set,
            an auto-generated filename is used with a timestamp.
        path : string
            The directory where the CSV files will be written.
            Default: "/tmp"
        """
        os.makedirs(path, exist_ok=True)
        if filename is None:
            filename = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

        self._base_filename = filename
        self._path = path
        self._file_handles = {}
        self.i = 0
        self._index_dim = index_dim
        self.rate = rate

    def update(self):
        if self.ports is not None:
            for name, port in self.ports.items():
                if not name.startswith("i"):
                    continue
                key = name[2:]
                file_path = os.path.join(self._path, f"{self._base_filename}-{key}.csv")

                if port.data is not None:

                    # Compute lengths of space and frequency
                    len_space = len(port.data.columns.get_level_values('space').unique())
                    len_frequency = len(port.data.columns.get_level_values('frequency').unique())
                    # Generate new columns with 'space' first then 'frequency'

                    # Reorder the columns to have space first and frequency second
                    port.data.columns = pd.MultiIndex.from_tuples([(space, freq) for freq, space in port.data.columns], names=["space", "freq"])
                    port.data = port.data.sort_index(axis=1, level=["space", "freq"])
                    # Flatten the MultiIndex columns for easier reading
                    port.data.columns = [f"{space}:{freq}" for space, freq in port.data.columns]
                    # Reset index and rename 'time' to include lengths and rate
                    port.data.reset_index(inplace=True)
                    time_col_name = f'time:{len_space}x{len_frequency}:{self.rate}'
                    port.data.rename(columns={'time': time_col_name}, inplace=True)

                    port.data['End Time'] = pd.to_datetime(port.data[time_col_name]) + pd.Timedelta(seconds=3)
                    # Convert 'Time' and 'End Time' to float
                    port.data[time_col_name] = pd.to_datetime(port.data[time_col_name]).astype('int64') / 1e9  # Convert to Unix time (seconds)
                    port.data['End Time'] = port.data['End Time'].astype('int64') / 1e9  # Convert to Unix time (seconds)
                    # Add new columns with NaN values
                    port.data['Event Id'] = np.nan
                    port.data['Event Date'] = np.nan
                    port.data['Event Duration'] = np.nan
                    # Reorder columns
                    cols = [time_col_name, 'End Time'] + [col for col in port.data.columns if col not in [time_col_name, 'End Time', 'Event Id', 'Event Date', 'Event Duration']] + ['Event Id', 'Event Date', 'Event Duration']
                    port.data = port.data[cols]

                    if file_path not in self._file_handles:
                        mode = 'w'
                        header = True
                    else:
                        mode = 'a'
                        header = False

                    port.data.to_csv(file_path, mode=mode, header=header, index=False)
                    self._file_handles[file_path] = True
                if port.meta:
                    self.i += 1
                    if self.i == 2:
                        raise WorkerInterrupt("interupting")

    def terminate(self):
        self._file_handles.clear()
        self.logger.debug('Cleaning up')
        time.sleep(1)
        self.logger.debug('Done')
