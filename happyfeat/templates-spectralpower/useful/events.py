import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError
from timeflux.core.node import Node
from timeflux.helpers.port import make_event, match_events, get_meta
from joblib import load
from time import time
import random
import pandas as pd
class Events(Node):

    def __init__(self, number_of_trials=4, first_class="OVTK_GDF_Left", second_class="OVTK_GDF_Right", baseline_duration=20, wait_for_beep_duration=1, wait_for_cue_duration=10, display_cue_duration=10, feedback_duration=5, end_of_trial_min_duration=2, end_of_trial_max_duration=5):
        super().__init__()
        self.number_of_trials = number_of_trials
        self.first_class = first_class
        self.second_class = second_class
        self.baseline_duration = baseline_duration
        self.wait_for_beep_duration = wait_for_beep_duration
        self.wait_for_cue_duration = wait_for_cue_duration
        self.display_cue_duration = display_cue_duration
        self.feedback_duration = feedback_duration
        self.end_of_trial_min_duration = end_of_trial_min_duration
        self.end_of_trial_max_duration = end_of_trial_max_duration
        self.sequence = []
        self.t = 0
        self.pending_stimulations = []  # Store pending stimulations
        self._initialize_sequence()
        timestamp = datetime.now(timezone.utc)
        self._run_experiment(timestamp)
        print('hello')


        

    def _initialize_sequence(self):
        self.sequence = [self.first_class, self.second_class] * self.number_of_trials
        random.seed(time())
        random.shuffle(self.sequence)


    def _send_stimulation(self, code, timestamp, name):
        # Ensure the timestamp is timezone-aware
        timestamp = self._convert_to_utc(timestamp)
        # Add stimulation to pending list
        self.pending_stimulations.append((code, timestamp, name))

    def _convert_to_utc(self, timestamp):
        """Ensure the timestamp is timezone-aware and in UTC."""
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    def _process_pending_stimulations(self):
        current_time = datetime.now(timezone.utc)
        to_send = []
        for stimulation in self.pending_stimulations:
            new_timestamp = self._convert_to_utc(stimulation[1])
            if new_timestamp <= current_time:
                to_send.append(stimulation)

        for stimulation in to_send:
            if self.first_class in stimulation:
                print('Checking if the first class is detected',stimulation)
            if self.second_class in stimulation:
                print('Checking if the second class is detected',stimulation)               
            code, timestamp, name = stimulation
            timestamp = pd.Timestamp(timestamp)+timedelta(hours=2)
            port_name = f"o_{name}"
            if hasattr(self, port_name):
                port = getattr(self, port_name)
                data = pd.DataFrame([[code, code]], index=[timestamp], columns=["label", "data"])
                port.data = data

            else:
                raise AttributeError(f"Port {port_name} does not exist")
            self.pending_stimulations.remove(stimulation)


    def update(self):

        self._process_pending_stimulations()

    def _run_experiment(self,timestamp):
        self.t = timestamp

        # Baseline management
        self._send_stimulation("OVTK_StimulationId_ExperimentStart", self.t, "experiment_start")
        self.t += timedelta(seconds=2)
        self._send_stimulation("OVTK_StimulationId_BaselineStart", self.t, "baseline_start")
        self._send_stimulation("OVTK_StimulationId_Beep", self.t, "beep")
        self.t += timedelta(seconds=self.baseline_duration)
        self._send_stimulation("OVTK_StimulationId_BaselineStop", self.t, "baseline_stop")
        self._send_stimulation("OVTK_StimulationId_Beep", self.t, "beep")
        print('self.sequence',self.sequence)
        # Trial management
        for i in range(self.number_of_trials * 2):
            self._send_stimulation("OVTK_GDF_Start_Of_Trial", self.t, "start_of_trial")
            self._send_stimulation("OVTK_GDF_Cross_On_Screen", self.t, "cross_on_screen")
            self.t += timedelta(seconds=self.wait_for_beep_duration)
            self._send_stimulation("OVTK_StimulationId_Beep", self.t, "beep")
            self.t += timedelta(seconds=self.wait_for_cue_duration)
            self._send_stimulation(self.sequence[i], self.t, "epochs")
            self.t += timedelta(seconds=self.display_cue_duration)
            self._send_stimulation("OVTK_GDF_Feedback_Continuous", self.t, "feedback_continuous")
            self.t += timedelta(seconds=self.feedback_duration)
            self._send_stimulation("OVTK_GDF_End_Of_Trial", self.t, "end_of_trial")
            self.t += timedelta(seconds=random.uniform(self.end_of_trial_min_duration, self.end_of_trial_max_duration))

        # End of experiment
        self._send_stimulation("OVTK_GDF_End_Of_Session", self.t, "end_of_session")
        self.t += timedelta(seconds=5)
        self._send_stimulation("OVTK_StimulationId_Train", self.t, "train")
        self.t += timedelta(seconds=1)
        self._send_stimulation("OVTK_StimulationId_ExperimentStop", self.t, "experiment_stop")

        
        