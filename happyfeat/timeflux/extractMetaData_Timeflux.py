import os
import pandas as pd
import subprocess
from shutil import copyfile
from importlib import resources
import mne
from happyfeat.lib.modifyOpenvibeScen import *
import sys 


def find_path( path):
    path = os.path.normpath(path)
    if os.path.isabs(path):
        if os.path.isfile(path):
            return path
    else:
        for base in sys.path:
            full_path = os.path.join(base, path)
            if os.path.isfile(full_path):
                return full_path
    raise FileNotFoundError(f"File `{path}` could not be found in the search path.")

def generateMetadata_timeflux(ovFile):
    
    # Check if the file path is valid
    # valid_path = find_path(ovFile)
    # Get the sampling frequency
    
    # Read the EDF file
    data = mne.io.read_raw_edf(ovFile, preload=True)
    rate = data.info['sfreq']
    # Convert data to a DataFrame
    data = data.to_data_frame(time_format='datetime')
    
    return list(data.columns)[1:], rate


if __name__ == '__main__':

    openvibeDesigner = "C:\\openvibeTestArthur\\dist\\x64\\Release\\openvibe-designer.cmd"

    testSig = "C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\motor-imagery.ov"
    generateMetadata(testSig, openvibeDesigner)

    testCsv = "C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\motor-imagery-META.csv"
    sampFreq, electrodeList = extractMetadata(testCsv)
    print("Sampling Freq: " + str(sampFreq))
    print("Electrodes (" + str(len(electrodeList)) + "): " + str(electrodeList))
