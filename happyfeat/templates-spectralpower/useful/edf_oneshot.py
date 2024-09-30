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
from scipy.signal import welch
class Replay(Node):

    def __init__(self, filename):

        self.logger = logging.getLogger(__name__)

        # Load store
        self.filename = self._find_path(filename)
        # Start timing the data loading process
        start_time = time.time()
        try:
            self.data = mne.io.read_raw_edf(self.filename, preload=True)
            # Define the new channel names
            new_channel_names = ['Fp1','Fz','F3','F7','FT9','FC5','FC1','C3','T7','FCz','CP5','CP1','Pz',
                                 'P3','P7','O1','Oz','O2','P4','P8','Fpz','CP6','CP2','Cz','C4','T8',
                                 'FT10','FC6','FC2','F4','F8','Fp2','AF7','AF3','AFz','F1','F5','FT7',
                                 'FC3','C1','C5','TP7','CP3','P1','P5','PO7','PO3','POz','PO4','PO8',
                                 'P6','P2','CPz','CP4','TP8','C6','C2','FC4','FT8','F6','AF8','AF4',
                                 'F2','Iz']
            # Rename the channels
            current_channel_names = self.data.ch_names
            print("the current channel names",current_channel_names)

            # if len(new_channel_names) != len(current_channel_names):
            #     raise ValueError("Number of new channel names must match the number of existing channels.")

            # rename_dict = dict(zip(current_channel_names, new_channel_names))
            # self.data.rename_channels(rename_dict)
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
        # Epoch_compute_MI_2_2 = self.select_Event('OVTK_GDF_Left',self.data,self.events,self.event_id,1,4,64)
        # Epoch_compute_Rest_2_2 = self.select_Event('OVTK_GDF_Right',self.data,self.events,self.event_id,1,4,64)
        # var_MI=Epoch_compute_MI_2_2.get_data()[:,7,:]
        # var_REST=Epoch_compute_Rest_2_2.get_data()[:,7,:]
        # print("get data epoch",Epoch_compute_MI_2_2.get_data().shape)
        # f_MI, Pxx_MI = welch(x=var_MI, fs=500, nfft=1024, axis=1)
        # f_REST, Pxx_REST = welch(x=var_REST, fs=500, nfft=1024, axis=1)
        # print("pxx_mi ",Pxx_MI.shape)
        # np.save('welchrest.npy',Pxx_REST[:,24])
        # np.save('welchmi.npy',Pxx_MI[:,24])


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
        filtered_events = [(event_time, event_id) for event_time, event_id in zip(event_times, self.events[:, 2]) if event_id in [5, 6,7]]
        
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


    def select_Event(self,event_name,RAW_data,events_from_annot,event_id,t_min,t_max,number_electrodes):

        epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin=t_min, tmax=t_max,preload=True,event_repeated='merge',baseline = None,picks = np.arange(0,number_electrodes))
        #epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin = t_min, tmax=t_max,preload=True,event_repeated='merge')
        return epochs_training[event_name]