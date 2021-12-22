import os
import mne
from Statistical_analysis import *
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
        electrodes = ['FP1','FP2','F7','F3','Fz','F4','F8','FC5','FC1','FC2','FC6','T7','C3','Cz','C4','T8','TP9','CP5','CP1','CP2','CP6','TP10','P7','P3','Pz','P4','P8','PO9','O1','Oz','O2','PO10','AF7','AF3','AF4','AF8','F5','F1','F2','F6','FT9','FT7','FC3','FC4','FT8','FT10','C5','C1','C2','C6','TP7','CP3','CPz','CP4','TP8','P5','P1','P2','P6','PO7','PO3','POz','PO4','PO8']
        for i in range(len(electrodes)):
            if (electrodes[i] == Ground):
                index_gnd = i
            if (electrodes[i] == Ref):
                index_ref = i
        electrodes[index_gnd] = 'AFz'
        electrodes[index_ref] = 'FCz'

    return electrodes

def load_file(sample_data_folder,filename):
    sample_Training_EDF = os.path.join(sample_data_folder, filename)
    raw_Training_EDF = mne.io.read_raw_edf(sample_Training_EDF, preload=True,verbose=False)
    raw_Training_EDF_CAR, ref_data = mne.set_eeg_reference(raw_Training_EDF, ref_channels='average')
    events_from_annot_1,event_id_1 = mne.events_from_annotations(raw_Training_EDF,event_id='auto')

    np.savetxt('raw_py.txt', raw_Training_EDF.get_data()[:,:25000], delimiter=',')
    np.savetxt('raw_py_CAR.txt', raw_Training_EDF_CAR.get_data()[:,:25000], delimiter=',')
    return raw_Training_EDF_CAR, events_from_annot_1,event_id_1

def load_file_eeg(sample_data_folder,filename):
    sample_Training_EDF = os.path.join(sample_data_folder, filename)
    raw_Training_EEG = mne.io.read_raw_nihon(sample_Training_EDF, preload=True, verbose=False)
    events_from_annot_1,event_id_1 = mne.events_from_annotations(raw_Training_EEG,event_id='auto')
    return raw_Training_EEG, events_from_annot_1,event_id_1


def select_Event(event_name,RAW_data,events_from_annot,event_id,t_min,t_max):
    if t_min == 0:
        epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin = t_min, tmax=t_max,preload=True,event_repeated='merge', baseline=None)
    else:
        epochs_training = mne.Epochs(RAW_data, events_from_annot, event_id,tmin = t_min, tmax=t_max,preload=True,event_repeated='merge')
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
            random_1 = 5*np.random.normal(size=len(time))
            random_2 = 5*np.random.normal(size=len(time))
            Signal_all_trials_1[j,i]=signal_al_1+random_1
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


def Extract_Data_to_compare(Data_Mi, Data_Rest, time, Trials, N_electrodes, Bins, n_window, shift):

    mat_left = Data_Mi
    Number_of_trials = Trials
    Number_of_electrodes = N_electrodes
    Number_of_Bins = Bins
    #shift = n_window - overlap
    length = round((time-n_window)/shift)
    time_leng = np.arange(0, time, shift)
    mat_left = mat_left[:, 2:]
    mat_left = mat_left[:, :Number_of_electrodes*Number_of_Bins]
    power_left = np.zeros([Number_of_trials, Number_of_electrodes, Number_of_Bins])

    time_left = np.zeros([Number_of_trials, Number_of_electrodes, length, Number_of_Bins])
    time_right = np.zeros([Number_of_trials, Number_of_electrodes, length, Number_of_Bins])

    for i in range(power_left.shape[0]):
        for j in range(power_left.shape[1]):
                power_left[i,j,:] = mat_left[(i*length):(i*length+length),(j*Number_of_Bins):(j*Number_of_Bins+Number_of_Bins)].mean(axis=0)
                time_left[i,j,:,:] = mat_left[(i*length):(i*length+length),(j*Number_of_Bins):(j*Number_of_Bins+Number_of_Bins)]

    mat_right = Data_Rest
    mat_right = mat_right[:,2:]
    mat_right = mat_right[:,:Number_of_electrodes*Number_of_Bins]
    power_right = np.zeros([Number_of_trials,Number_of_electrodes,Number_of_Bins])

    for i in range(power_left.shape[0]):
        for j in range(power_left.shape[1]):
                power_right[i,j,:] = mat_right[(i*length):(i*length+length),(j*Number_of_Bins):(j*Number_of_Bins+Number_of_Bins)].mean(axis=0)
                time_right[i,j,:,:] = mat_right[(i*length):(i*length+length),(j*Number_of_Bins):(j*Number_of_Bins+Number_of_Bins)]

    return power_right, power_left,time_left,time_right,time_leng
