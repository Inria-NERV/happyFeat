"""timeflux.nodes.csv: CSV nodes"""

import pandas as pd
import os
import time
from timeflux.core.node import Node
import xarray as xr
from timeflux.core.exceptions import ValidationError, WorkerInterrupt

class SaveToCSV(Node):
    """Save to CSV files."""

    def __init__(self, filename=None, path="/tmp"):
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



    def update(self):

        if self.ports is not None:

            for name, port in self.ports.items():
                
                if not name.startswith("i"):
                    continue
                key = name[2:]
                file_path = os.path.join(self._path, f"{self._base_filename}.csv")

                if port.data is not None:

                    #print("I received the data for simulation:",key)
                    if file_path not in self._file_handles:
                        mode = 'w'
                        header = True
                    else:
                        
                        mode = 'a'
                        header = False

                    if isinstance(port.data, xr.DataArray):
                        data = port.data.values
                        #print(port.data)
                        index = port.data.coords["time"].values
                        columns = port.data.coords["frequency"].values
                        space=port.data.coords["space"].values
                        # Flatten the data to 2D: (time*space) x frequency
                        flattened_data = data.reshape(-1, data.shape[2])

                        # Create a MultiIndex for the DataFrame using time and space
                        multi_index = pd.MultiIndex.from_product([index, space], names=["time", "space"])
                        # Create DataFrame
                        # Create DataFrame
                        df = pd.DataFrame(flattened_data.T, index=multi_index, columns=columns)
                        #df = pd.DataFrame(data[0].T, index=index, columns=columns)
                        df["class"]=key
                        df.to_csv(file_path, mode=mode, header=header, index=True)
                    elif isinstance(port.data, pd.DataFrame):
                        port.data["Class"]=key
                        port.data.to_csv(file_path, mode=mode, header=header, index=True)
                    self._file_handles[file_path] = True


    def terminate(self):
        self._file_handles.clear()
