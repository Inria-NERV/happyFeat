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

    def __init__(self, filename):

        self.logger = logging.getLogger(__name__)

        # Load store
        self.filename = self._find_path(filename)
        # Start timing the data loading process
        start_time = time.time()
        
        try:
            self.data = mne.io.read_raw_edf(self.filename, preload=True)
        except IOError as e:
            raise WorkerInterrupt(e)

        # End timing the data loading process
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time taken to load data: {elapsed_time:.2f} seconds")

        # Extract events
        self.events, self.event_id = mne.events_from_annotations(self.data)
        self.events_df = self._create_events_df()
        self.counter=0

    def update(self):
        self.counter+=1
        if self.counter==1:
            data=self.data.to_data_frame(time_format='datetime')
            data.set_index('time', inplace=True)
            events=self.events_df.copy(deep=True)
            events.set_index('time',inplace=True)
            if (not data is None) and (not events is None):
                getattr(self, "o_raw").data = data
                getattr(self, "o_events").data = events

        # data=self.data.to_data_frame(time_format='datetime')
        # data.set_index('time', inplace=True)
        # events=self.events_df.copy(deep=True)
        # events.set_index('time',inplace=True)
        # if (not data is None) and (not events is None):
        #     getattr(self, "o_raw").data = data
        #     getattr(self, "o_events").data = events
        #     self.o_raw.clear()
        #     self.o_events.clear()


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

    def terminate(self):
        self.data.close()
