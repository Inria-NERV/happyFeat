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

    def __init__(self, filenames):
        """
        Initialize.

        Parameters
        ----------
        filename : string
            The name of the CSV file to read.
        """
        self.filenames = filenames
        self.data = []
        self.times = []
        self.count=0

    def update(self):
        self.count+=1
        listSampFreq = []
        listElectrodeList = []
        listFreqRange = []
        if self.count==1:
            try:

                for filename in self.filenames:
                    header, data = load_csv_np(filename)

                    # Extract time information
                    time_col_index = 0  # The index of the time column in the data
                    # time = pd.to_datetime(data[:, time_col_index], unit='s')
                    time=data[:, time_col_index]
                    # print(data[:, time_col_index])
                    # print(time)
                    self.times.append(time)

                    # Extract sampling frequency
                    sampFreq = int(header[0].split(":")[-1])
                    listSampFreq.append(sampFreq)

                    # Extract space and frequency information
                    freq_space = header[2:-3]
                    freq = np.unique([float(col.split(':')[-1]) for col in freq_space])
                    space = np.unique([col.split(':')[0] for col in freq_space]).astype('object')
                    listElectrodeList.append(space)
                    listFreqRange.append(freq)
                    
                    # Determine the shape of the data
                    n_samples = len(time)
                    n_freq = len(freq)
                    n_space = len(space)
                    # print("csv brut data",data.shape)
                    # Reshape data
                    ### Attention ! Critical reshape situation the reshape should be in coherence with the csv file header structure and the timelfux port data array structure 
                    reshaped_data = data.reshape((n_samples,  n_space,n_freq)).transpose(0,2,1)
                    self.data.append(reshaped_data)

                # Check for consistency in sampling frequency
                if not all(freq == listSampFreq[0] for freq in listSampFreq):
                    errMsg = "Error when loading CSV files\nSampling frequency mismatch ({})".format(listSampFreq)
                    self.over.emit(False, errMsg)
                    return

                # Check for consistency in electrode list
                if not all(np.array_equal(electrodes, listElectrodeList[0]) for electrodes in listElectrodeList):
                    errMsg = "Error when loading CSV files\nElectrode List mismatch"
                    self.over.emit(False, errMsg)
                    return

                # Check for consistency in frequency list
                if not all(np.array_equal(frequency, listFreqRange[0]) for frequency in listFreqRange):
                    errMsg = "Error when loading CSV files\nfrequency list mismatch"
                    self.over.emit(False, errMsg)
                    return

                # Concatenate data and times across files
                self.data = np.concatenate(self.data, axis=0)
                self.times = np.concatenate(self.times).astype('datetime64[ns]')


                # Create the DataArray
                data_array = xr.DataArray(
                    self.data,
                    coords={
                        'time': self.times,
                        'frequency': freq.astype('float64'),
                        'space': space.astype('object')
                    },
                    dims=["time", "frequency", "space"]
                )

                # Extract label from filename
                base, ext = os.path.splitext(self.filenames[0])
                parts = base.split('-')
                label = parts[-1]
                label_array = np.array([label] * len(self.data), dtype=object)

                # Assign the DataArray and metadata to the output port
                getattr(self, "o").data = data_array
                getattr(self, "o").meta = {'label': label_array}
 
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
