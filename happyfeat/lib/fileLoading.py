import os
import time
import numpy as np
import mne
import pandas as pd
def channel_generator(number_of_channel, Ground, Ref):
    if number_of_channel == 32:
        electrodes = ['Fp1','Fp2','F7','F3','Fz','F4','F8','FC5','FC1','FC2','FC6','T7','C3','Cz','C4','T8','TP9','CP5','CP1','CP2','CP6','TP10','P7','P3','Pz','P4','P8','PO9','O1','Oz','O2','PO10']
        for i in range(len(electrodes)):
            if (electrodes[i] == Ground):
                index_gnd = i
            if (electrodes[i] == Ref):
                index_ref = i
        electrodes[index_gnd] = 'AFz'
        electrodes[index_ref] = 'FCz'

    if number_of_channel == 64:
        #electrodes = ['FP1','FP2','F7','F3','Fz','F4','F8','FC5','FC1','FC2','FC6','T7','C3','Cz','C4','T8','TP9','CP5','CP1','CP2','CP6','TP10','P7','P3','Pz','P4','P8','PO9','O1','Oz','O2','PO10','AF7','AF3','AF4','AF8','F5','F1','F2','F6','FT9','FT7','FC3','FC4','FT8','FT10','C5','C1','C2','C6','TP7','CP3','CPz','CP4','TP8','P5','P1','P2','P6','PO7','PO3','POz','PO4','PO8']
        electrodes = ['Fp1','Fz','F3','F7','FT9','FC5','FC1','C3','T7','TP9','CP5','CP1','Pz','P3','P7','O1','Oz','O2','P4','P8','TP10','CP6','CP2','Cz','C4','T8','FT10','FC6','FC2','F4','F8','Fp2','AF7','AF3','AFz','F1','F5','FT7','FC3','C1','C5','TP7','CP3','P1','P5','PO7','PO3','POz','PO4','PO8','P6','P2','CPz','CP4','TP8','C6','C2','FC4','FT8','F6','AF8','AF4','F2','Iz']
        for i in range(len(electrodes)):
            if (electrodes[i] == Ground):
                index_gnd = i
            if (electrodes[i] == Ref):
                index_ref = i
        electrodes[index_gnd] = 'Fpz'
        electrodes[index_ref] = 'FCz'

    return electrodes

def load_file(sample_data_folder,filename,car_bool):
    sample_Training_EDF = os.path.join(sample_data_folder, filename)
    raw_Training_EDF = mne.io.read_raw_edf(sample_Training_EDF, preload=True,verbose=False)
    if car_bool:
        raw_Training_EDF_CAR, ref_data = mne.set_eeg_reference(raw_Training_EDF, ref_channels='average')
        events_from_annot_1,event_id_1 = mne.events_from_annotations(raw_Training_EDF_CAR,event_id='auto')
        return raw_Training_EDF_CAR, events_from_annot_1,event_id_1
    else:
        #raw_Training_EDF_CAR, ref_data = mne.set_eeg_reference(raw_Training_EDF, ref_channels='average')
        events_from_annot_1,event_id_1 = mne.events_from_annotations(raw_Training_EDF,event_id='auto')
        return raw_Training_EDF, events_from_annot_1,event_id_1

def load_file_eeg(sample_data_folder,filename):
    sample_Training_EDF = os.path.join(sample_data_folder, filename)
    raw_Training_EEG = mne.io.read_raw_nihon(sample_Training_EDF, preload=True, verbose=False)
    events_from_annot_1,event_id_1 = mne.events_from_annotations(raw_Training_EEG,event_id='auto')
    return raw_Training_EEG, events_from_annot_1,event_id_1


def select_Event(event_name,RAW_data,events_from_annot,event_id,t_min,t_max,number_electrodes):

    epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin=t_min, tmax=t_max,preload=True,event_repeated='merge',baseline = None,picks = np.arange(0,number_electrodes))

        #epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin = t_min, tmax=t_max,preload=True,event_repeated='merge')
    return epochs_training[event_name]


def Session_generation_Signal(Number_of_runs,Electrolde_number,alpha_band,beta_band,fs, Amp_alpha,Amp_beta):
    freq_al_1 = alpha_band
    amp_al = 10
    freq_beta_1 = beta_band
    amp_beta = 30
    time = np.arange(0, 15, 1/fs)
    Signal_all_trials_1 = np.zeros([Number_of_runs,Electrolde_number,len(time)])
    Signal_all_trials_2 = np.zeros([Number_of_runs,Electrolde_number,len(time)])
    signal_al_1 = Amp_alpha*np.sin(2*np.pi*freq_al_1*time)  #+ Amp_beta*np.sin(2*np.pi*freq_beta_1*time)
    signal_al_2 = Amp_beta*np.sin(2*np.pi*freq_beta_1*time)
    for j in range(Number_of_runs):
        for i in range(Electrolde_number):

            random_1 = 100*np.random.normal(size=len(time))
            random_2 = 100*np.random.normal(size=len(time))
            Signal_all_trials_1[j,i]= random_1
            Signal_all_trials_2[j,i] = random_2
            if(i == 10):
                Signal_all_trials_1[j,i]=signal_al_1+random_1
                Signal_all_trials_2[j,i] = random_2

            if (i == 20):
                Signal_all_trials_1[j,i]=random_1
                Signal_all_trials_2[j,i] = signal_al_2+random_2


            fourier_transform = np.fft.rfft(signal_al_1)
            fourier_transform_2 = np.fft.rfft(signal_al_2)

            abs_fourier_transform = np.abs(fourier_transform)
            abs_fourier_transform_2 = np.abs(fourier_transform_2)

            power_spectrum = np.square(abs_fourier_transform)
            power_spectrum_2 = np.square(abs_fourier_transform_2)
            frequency = np.linspace(0, fs/2, len(power_spectrum))
    return Signal_all_trials_1,Signal_all_trials_2


def load_csv_cond(file):
    # Read data from file 'filename.csv'
    # (in the same directory that your python process is based)
    # Control delimiters, rows, column names with read_csv (see later)
    data = pd.read_csv(file)
    # Preview the first 5 lines of the loaded data
    data.head()
    return data


