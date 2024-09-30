import os
import sys
import datetime
import pandas as pd
import numpy as np
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError
from timeflux.core.node import Node
import mne
import timeflux.helpers.clock as clock
import time
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError
from timeflux.core.node import Node

# Ignore the "object name is not a valid Python identifier" message
import warnings
from tables.exceptions import NaturalNameWarning
class EDFReader(Node):
    """Node that reads EDF files and outputs the data and events.

    This node reads an EDF file using MNE, extracts the raw data and events, 
    and then outputs them through the Timeflux ports.

    Args:
        filename (str): Path to the EDF file.
        rate (int): Number of samples to include in each chunk. Default: 500.

    Attributes:
        o (Port): Default output for data, provides a pandas.DataFrame with raw data.
        o_events (Port): Events output, provides a pandas.DataFrame with events.

    """

    def __init__(self, filename, rate=500):
        super().__init__()

        self.filename = self._find_path(filename)
        self.rate = rate

        # Load EDF file
        try:
            self.data = mne.io.read_raw_edf(self.filename, preload=True)
        except IOError as e:
            raise WorkerInterrupt(e)

        # Extract raw data
        self.frame = self.data.to_data_frame(time_format='datetime')

        # Convert 'time' column to datetime
        self.frame['time'] = pd.to_datetime(self.frame['time'])

        # Calculate time differences
        self.frame['time_diff'] = self.frame['time'].diff().fillna(pd.Timedelta(seconds=0))

        # Initialize current time
        current_time = pd.Timestamp.now()

        # Create index with time differences added
        self.frame['index'] = current_time
        for i in range(1, len(self.frame)):
            self.frame.at[self.frame.index[i], 'index'] = self.frame.at[self.frame.index[i-1], 'index'] + self.frame.at[self.frame.index[i], 'time_diff']
        self.frame['index'] = pd.to_datetime(self.frame['index'])
        #print(self.frame)
        # Extract events
        self.events, self.event_id = mne.events_from_annotations(self.data)
        self.events_df = self._create_events_df()
         # Convert 'time' column to datetime and set as index
        self.events_df['time'] = pd.to_datetime(self.events_df['time'])

        # Merge events_df with frame to get the 'index' column
        self.events_df = pd.merge_asof(self.events_df, self.frame[['time', 'index']], on='time', direction='nearest')
        self.events_df['index'] = pd.to_datetime(self.events_df['index'])
        self.frame.set_index('index', inplace=True)
        self.events_df.set_index('index', inplace=True)

        # Initialize the current position
        self._current = 0


    def update(self):
        # Output data in chunks
        if self._current < len(self.frame):
            chunk = self.frame.iloc[self._current:self._current + self.rate]
            #print("chunk is",chunk)
            # Drop 'time' and 'time_diff' columns
            chunk.drop(columns=['time', 'time_diff'], inplace=True, errors='ignore')
            self.o.set(chunk, timestamps=chunk.index, names=chunk.columns)
            self._current += self.rate
        else:
            raise WorkerInterrupt("No more data.")

        # Output events
        current_time_event = self.frame.index[self._current - 1]  # Get the current time index
        #print('this is cuurenttimeevent',current_time_event)
        #print('indx du truc',self.events_df.index[0])
        events_chunk = self.events_df[self.events_df.index <= current_time_event]
        if not events_chunk.empty:
            events_chunk.drop(columns=['time', 'time_diff'], inplace=True, errors='ignore')
            self.o_events.set(events_chunk, timestamps=events_chunk.index, names=events_chunk.columns)

    def terminate(self):
        pass

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

    def _create_events_df(self):
        sfreq = self.data.info['sfreq']
        start_time = self.data.info['meas_date']
        if isinstance(start_time, tuple):
            start_time = start_time[0]
        start_time = pd.to_datetime(start_time)  # Convert start_time to datetime

        event_times = self._samples_to_datetime(self.events[:, 0], start_time, sfreq)
        
        # Filter events
        filtered_events = [(event_time, event_id) for event_time, event_id in zip(event_times, self.events[:, 2]) if event_id in [5, 6]]
        
        # Separate the filtered events into lists
        event_times_filtered, event_ids_filtered = zip(*filtered_events)
        
        # Create labels and data based on filtered event IDs
        labels = [f"stimulus_{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}" for event_id in event_ids_filtered]
        data = [{"info": f"{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}"} for event_id in event_ids_filtered]

        # Create DataFrame
        events_df = pd.DataFrame({
            'time': event_times_filtered,
            'label': labels,
            'data': data
        })

        return events_df

    def _samples_to_datetime(self, samples, start_time, sfreq):
        return start_time + pd.to_timedelta(samples / sfreq, unit='s')



import pandas as pd
import numpy as np
import mne
import os
import sys
import logging
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError

import pandas as pd
import numpy as np
import mne
import os
import sys
import logging
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError

class Replay(Node):
    """Replay a HDF5 file."""

    def __init__(self, filename, key, speed=0.5, timespan=None, resync=True, start=0):
        """
        Initialize.

        Parameters
        ----------
        filename : string
            The path to the HDF5 file.
        keys: list
            The list of keys to replay.
        speed: float
            The speed at which the data must be replayed. 1 means real-time.
            Default: 1
        timespan: float
            The timespan of each chunk, in seconds.
            If not None, will take precedence over the `speed` parameter
            Default: None
        resync: boolean
            If False, timestamps will not be resync'ed to current time
            Default: True
        start: float
            Start directly at the given time offset, in seconds
            Default: 0
        """
        self.logger = logging.getLogger(__name__)

        # Load store
        self.filename = self._find_path(filename)
        try:
            self.data = mne.io.read_raw_edf(self.filename, preload=True)
        except IOError as e:
            raise WorkerInterrupt(e)

        # Init
        self._sources = {}
        self._start = pd.Timestamp.max.tz_localize(None)
        self._stop = pd.Timestamp.min.tz_localize(None)
        self._speed = speed
        self._timespan = None if not timespan else pd.Timedelta(f"{timespan}s")
        self._resync = resync

        # Get first 
        self.frame = self.data.to_data_frame(time_format='datetime')
        self.frame['time'] = pd.to_datetime(self.frame['time'])  # Ensure 'time' column is datetime



        first = self.frame['time'][0].tz_localize(None)
        # Get last index
        nrows = len(self.frame['time'])
        last = self.frame['time'][nrows - 1].tz_localize(None)
        # Extract events
        self.events, self.event_id = mne.events_from_annotations(self.data)
        self.events_df = self._create_events_df()
         # Convert 'time' column to datetime and set as index
        self.events_df['time'] = pd.to_datetime(self.events_df['time'])

        # Check index type
        if not isinstance(first, pd.Timestamp):
            self.logger.warning("Invalid index. Will be skipped.")
        
        # Find lowest and highest indices across stores
        if first < self._start:
            self._start = first
        if last > self._stop:
            self._stop = last
        
        # Extract meta
        if self.data.info is not None:
            meta = {"rate": self.data.info['sfreq']}
        else:
            meta = {}
        
        # Set output port name, port will be created dynamically
        name = "o_" + key

        
        # Update sources
        self._sources[key] = {
            "start": first,
            "stop": last,
            "nrows": nrows,
            "name": name,
            "meta": meta,
        }

        # Current time
        now = pd.Timestamp.now()
        
        # Starting timestamp
        self._start += pd.Timedelta(f"{start}s")
        
        # Time offset
        self._offset = now - self._start
        
        # Current query time
        self._current = self._start
        
        # Last update
        self._last = now
        
        # print(f"Initialized Replay with start time: {self._start}, stop time: {self._stop}")

    def update(self):
        if self._current > self._stop:
            raise WorkerInterrupt("No more data.")

        min_time = self._current

        if self._timespan:
            max_time = min_time + self._timespan
        else:
            now = pd.Timestamp.now()
            elapsed = now - self._last
            max_time = min_time + elapsed * self._speed
            self._last = now

        # print(f"Updating from {min_time} to {max_time}")

        for key, source in self._sources.items():
            # Select data
            try:
                data = self.frame[
                (self.frame['time'].apply(lambda x: x.tz_localize(None)) >= min_time) &
                (self.frame['time'].apply(lambda x: x.tz_localize(None)) < max_time)].copy()
                events = self.events_df[
                (self.events_df['time'].apply(lambda x: x.tz_localize(None)) >= min_time) &
                (self.events_df['time'].apply(lambda x: x.tz_localize(None)) < max_time)].copy()
                # if events.empty == False:
                #     print(events)
            except Exception as e:
                self.logger.error(f"Error selecting data: {e}")
                raise

            self.logger.debug(f"Selected data range: {data}")

            # Add offset
            if self._resync:
                data['time'] = data['time'] + self._offset
                events['time'] = events['time'] + self._offset
            print("the meta",events.set_index('time'))
            # Update port
            getattr(self, source["name"]).data = data.set_index('time')
            getattr(self, source["name"]).meta = source["meta"]
            getattr(self, "o_events").data = events.set_index('time')

        self._current = max_time
        self.logger.debug(f"Set current time to {self._current}")

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
    def _create_events_df(self):
        sfreq = self.data.info['sfreq']
        start_time = self.data.info['meas_date']
        if isinstance(start_time, tuple):
            start_time = start_time[0]
        start_time = pd.to_datetime(start_time)  # Convert start_time to datetime

        event_times = self._samples_to_datetime(self.events[:, 0], start_time, sfreq)
        
        # Filter events
        filtered_events = [(event_time, event_id) for event_time, event_id in zip(event_times, self.events[:, 2]) if event_id in [5, 6]]
        
        # Separate the filtered events into lists
        event_times_filtered, event_ids_filtered = zip(*filtered_events)
        
        # Create labels and data based on filtered event IDs
        labels = [f"{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}" for event_id in event_ids_filtered]
        data = [f"{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}" for event_id in event_ids_filtered]

        # Create DataFrame
        events_df = pd.DataFrame({
            'time': event_times_filtered,
            'label': labels,
            'data': data
        })

        return events_df

    def _samples_to_datetime(self, samples, start_time, sfreq):
        return start_time + pd.to_timedelta(samples / sfreq, unit='s')


class EDFReader_class1(Node):
    """Node that reads EDF files and outputs the data and events.

    This node reads an EDF file using MNE, extracts the raw data and events, 
    and then outputs them through the Timeflux ports.

    Args:
        filename (str): Path to the EDF file.
        ra (int): Number of samples to include in each chunk. Default: 500.

    Attributes:
        o (Port): Default output for data, provides a pandas.DataFrame with raw data.
        o_events (Port): Events output, provides a pandas.DataFrame with events.

    """

    def __init__(self, filename, rate=500):
        super().__init__()

        self.filename = self._find_path(filename)
        self.rate = rate

        # Load EDF file
        try:
            self.data = mne.io.read_raw_edf(self.filename, preload=True)
        except IOError as e:
            raise WorkerInterrupt(e)

        # Extract raw data
        self.raw_data = self.data.get_data()
        self.frame = self.data.to_data_frame(time_format='datetime')

        # Convert 'time' column to datetime
        self.frame['time'] = pd.to_datetime(self.frame['time'])
        self.frame.set_index('time', inplace=True)  # Set the time as index

        # Extract events
        self.events, self.event_id = mne.events_from_annotations(self.data)
        self.events_df = self._create_events_df()

        # Initialize the current position
        self._current = 0

    def update(self):
        # Output data in chunks
        if self._current < len(self.frame):
            chunk = self.frame.iloc[self._current:self._current + self.rate]
            self.o.set(chunk,timestamps=chunk.index,names=chunk.columns)
            self._current += self.rate
        else:
            raise WorkerInterrupt("No more data.")

        # Output events
        current_time = self.frame.index[self._current - 1]  # Get the current time index

        events_chunk = self.events_df[self.events_df.index <= current_time]
        if not events_chunk.empty:
            self.o_events.set(events_chunk,timestamps=events_chunk.index,names=events_chunk.columns)
        

    def terminate(self):
        pass

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

    def _create_events_df(self):
        sfreq = self.data.info['sfreq']
        start_time = self.data.info['meas_date']
        if isinstance(start_time, tuple):
            start_time = start_time[0]
        start_time = pd.to_datetime(start_time)  # Convert start_time to datetime

        event_times = self._samples_to_datetime(self.events[:, 0], start_time, sfreq)
        # Convert events to DataFrame with 'label' and 'data'
        events_list = []
        for event_time, event_id in zip(event_times, self.events[:, 2]):
            if event_id in [5, 6]:
                label = f"stimulus_{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}"
                data = {"info": f"{list(self.event_id.keys())[list(self.event_id.values()).index(event_id)]}"}
                events_list.append([event_time, label, data])

        events_df = pd.DataFrame(events_list, columns=['time', 'label', 'data'])

        events_df.set_index('time', inplace=True)
        #print(events_df)
        return events_df

    def _samples_to_datetime(self, samples, start_time, sfreq):
        return start_time + pd.to_timedelta(samples / sfreq, unit='s')