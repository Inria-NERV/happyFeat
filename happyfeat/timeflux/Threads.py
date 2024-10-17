import sys
import os
import time
import re
import subprocess
import platform
from shutil import copyfile
from importlib import resources

from PySide2 import QtCore
from PySide2.QtCore import Signal
from happyfeat.timeflux.modifyYamFile import modify_extraction_yaml_new,update_filenames,update_online_scenario
from happyfeat.lib.mergeRunsCsv import mergeRunsCsv, mergeRunsCsv_new
from happyfeat.lib.extractMetaData import extractMetadata, generateMetadata

from happyfeat.lib.modifyOpenvibeScen import *
from happyfeat.lib.Visualization_Data import *
from happyfeat.lib.featureExtractUtils import *
from happyfeat.lib.utils import *

from happyfeat.lib.bcipipeline_settings import *
from happyfeat.timeflux.extractMetaData_Timeflux import *

# ------------------------------------------------------
# CLASSES FOR LONG-RUNNING OPERATIONS IN THREADS
# ------------------------------------------------------



class Extraction_Timeflux(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

    def __init__(self, scenFile, signalFiles, signalFolder,
                 parameterDict, currentSessionId, parent=None):

        super().__init__(parent)
        self.stop = False
        self.scenFile = scenFile
        self.signalFiles = signalFiles
        self.signalFolder = signalFolder
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = currentSessionId
        self.extractDict = parameterDict["Sessions"][currentSessionId]["ExtractionParams"].copy()

    def run(self):

        for signalFile in self.signalFiles:
            tstart = time.perf_counter()

            self.info2.emit(str("Extracting data for file " + signalFile + "..."))

            # Verify the existence of metadata files for each selected files,
            # and if not, generate them.
            # Then extract sampling frequency and electrode list
            sampFreq = None
            electrodeList = None
            electrodeList, sampFreq = generateMetadata_timeflux(os.path.join(self.signalFolder, signalFile))
            # Check everything went ok...
            if not sampFreq:
                errMsg = str("Error while loading metadata CSV file for session " + signalFile)
                self.over.emit(False, errMsg)
                return

            ## MODIFY THE EXTRACTION SCENARIO with entered parameters
            self.extractDict["ChannelNames"] = electrodeList

            # Modify extraction scenario to use provided signal file, and rename outputs accordingly
            filename = signalFile.removesuffix(".edf")
            outputSpect = str(filename + "-SPECTRUM")
            csv_file_path = os.path.join(os.path.split(self.signalFolder)[0], "sessions", self.currentSessionId, "extract")
            reader_yaml_file_path = os.path.join(os.path.split(self.signalFolder)[0], "EDF_Reader_oneshot.yaml")
            extraction_yaml_file_path = os.path.join(os.path.split(self.signalFolder)[0], self.scenFile)

            # Here, "trim samples" (provided to the "Dynamic Output" TF node)
            # corresponds to the number of samples considered for PSD estimation *at the end*
            # of the window.
            # (ex: for a 4s trial window at 500Hz, trim_samples = 1500 will cut out the 3 last seconds
            # of signal for estimation)
            trim_samples = int( float(self.extractDict["StimulationEpoch"]) * sampFreq )

            nfft = int( sampFreq / float(self.extractDict["FreqRes"]))  # TODO : closest superior power of 2 ?

            ## modify yaml file
            # Notes:
            # Epoching : "before" is really *before* the stimulation (so here we need 0.0s)
            # Epoching : "after" is after. :)
            modify_extraction_yaml_new(
                extraction_yaml_file_path,
                filename=os.path.join(self.signalFolder, signalFile),
                rate=1,
                keys=self.extractDict["ChannelNames"],
                epoch_params={'before': 0.0, 'after': float(self.extractDict["StimulationEpoch"])+float(self.extractDict["StimulationDelay"])},
                trim_samples=trim_samples,
                welch_rate=sampFreq,
                recorder_filename=outputSpect,
                path=csv_file_path,
                nfft=nfft
            )

            # Launch timeflux scenario !
            p = subprocess.Popen([ "timeflux", "-d", str(extraction_yaml_file_path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)  # add cwd if needed

            # Print console output, and detect end of process...
            while True:
                output = p.stdout.readline()
                if p.poll() is not None:
                    break
                if output:
                    print(str(output))
                    if "Terminated" in str(output):
                        p.kill()
                        break

            self.info.emit(True)    # send "info" signal to increment progressbar
            tstop = time.perf_counter()
            print("= Extraction from file " + filename + " finished in " + str(tstop-tstart))

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True


# Get POWER SPECTRUM data from a CSV, generated by the "extraction" part of the software
def Extract_CSV_Data_Timeflux(data_cond, nbElectrodes, bins):

    length = 1
    data = data_cond[:, 2:]
    data = data[:, :nbElectrodes * bins]

    nbTrials = np.shape(data)[0]

    power = np.zeros([nbTrials, nbElectrodes, bins])
    timefreq = np.zeros([nbTrials, nbElectrodes, length, bins])

    for i in range(power.shape[0]):
        for j in range(power.shape[1]):
            power[i, j, :] = data[(i * length):(i * length + length), (j * bins):(j * bins + bins)].mean(axis=0)
            timefreq[i, j, :, :] = data[(i * length):(i * length + length), (j * bins):(j * bins + bins)]

    return power, timefreq

class LoadFilesForVizPowSpectrum_Timeflux(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str, list)

    def __init__(self, analysisFiles, workingFolder, parameterDict, Features, sampFreq, parent=None):

        super().__init__(parent)
        self.stop = False
        self.analysisFiles = analysisFiles
        self.workingFolder = workingFolder
        self.parameterDict = parameterDict.copy()
        self.extractDict = parameterDict["Sessions"][parameterDict["currentSessionId"]]["ExtractionParams"].copy()
        self.Features = Features
        self.samplingFreq = sampFreq
        self.useBaselineFiles = False

        self.dataNp1 = []
        self.dataNp2 = []

    def run(self):

        listSampFreq = []
        listElectrodeList = []
        listFreqBins = []
        idxFile = 0

        # TODO : so far no baseline files, will integrate time-freq maps later
        # self.useBaselineFiles = self.parameterDict["pipelineType"] == optionKeys[1]
        self.useBaselineFiles = False

        # load files per class
        validFiles = []
        for selectedFilesForViz in self.analysisFiles:
            idxFile += 1
            pipelineLabel = "SPECTRUM"
            class1label = self.parameterDict["AcquisitionParams"]["Class1"]
            class2label = self.parameterDict["AcquisitionParams"]["Class2"]
            selectedBasename = selectedFilesForViz

            path1 = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self. workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))
            self.info2.emit(str("Loading " + pipelineLabel + " Data for file " + str(idxFile) + " : " + selectedFilesForViz))
            [header1, data1] = load_csv_np(path1)
            [header2, data2] = load_csv_np(path2)

            # Sampling frequency
            # Infos in the columns header of the CSVs in format "Time:32x251:500"
            # (Column zero contains starting time of the row)
            # 32 is channels, 251 is freq bins, 500 is sampling frequency)
            sampFreq1 = int(header1[0].split(":")[-1])
            sampFreq2 = int(header2[0].split(":")[-1])
            freqBins1 = int(header1[0].split(":")[1].split("x")[1])
            freqBins2 = int(header2[0].split(":")[1].split("x")[1])
            if sampFreq1 != sampFreq2 or freqBins1 != freqBins2:
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "\nSampling frequency or frequency bins mismatch")
                errMsg = str(errMsg + "\n(" + str(sampFreq1) + " vs " + str(sampFreq2) + " or ")
                errMsg = str(errMsg + str(freqBins1) + " vs " + str(freqBins2) + ")")
                self.over.emit(False, errMsg, None)
                return

            listSampFreq.append(sampFreq1)
            listFreqBins.append(freqBins1)

            elecTemp1 = header1[2:-3]
            elecTemp2 = header2[2:-3]
            electrodeList1 = []
            electrodeList2 = []
            for i in range(0, len(elecTemp1), freqBins1):
                electrodeList1.append(elecTemp1[i].split(":")[0])
                electrodeList2.append(elecTemp2[i].split(":")[0])

            if electrodeList1 != electrodeList2:
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "\nElectrode List mismatch")
                self.over.emit(False, errMsg, None)
                return

            listElectrodeList.append(electrodeList1)

            # check for invalid values...
            newData1, valid1 = check_valid_np(data1)
            newData2, valid2 = check_valid_np(data2)

            if valid1 and valid2:
                validFiles.append(True)
            else:
                validFiles.append(False)

            self.dataNp1.append(data1)
            self.dataNp2.append(data2)

            self.info.emit(True)

        # Check if all files have the same sampling freq and electrode list. If not, for now, we don't process further
        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg, None)
            return
        else:
            self.samplingFreq = listSampFreq[0]
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Electrode List mismatch")
            self.over.emit(False, errMsg, None)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        if not all(freqBins == listFreqBins[0] for freqBins in listFreqBins):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Not same number of frequency bins (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg, None)
            return
        else:
            print("Frequency bins: " + str(listFreqBins[0]))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.extractDict["StimulationEpoch"])  # TODO : for time-freq time array
        trials = int(self.parameterDict["AcquisitionParams"]["TrialNb"])  # TODO : for time-freq time array
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqBins[0]

        # For multiple runs (ie. multiple selected CSV files), we just concatenate
        # the trials from all files. Then the displayed spectral features (R²map, PSD, topography)
        # will be computed as averages over all the trials.
        power_cond1_final = None
        power_cond2_final = None
        timefreq_cond1_final = None
        timefreq_cond2_final = None
        idxFile = 0
        for run in range(len(self.dataNp1)):
            idxFile += 1
            self.info2.emit(str("Processing data for file " + str(idxFile)))
            power_cond1, timefreq_cond1 = \
                Extract_CSV_Data_Timeflux(self.dataNp1[run], nbElectrodes, n_bins)
            power_cond2, timefreq_cond2 = \
                Extract_CSV_Data_Timeflux(self.dataNp2[run], nbElectrodes, n_bins)

            if power_cond1_final is None:
                power_cond1_final = power_cond1
                power_cond2_final = power_cond2
                timefreq_cond1_final = timefreq_cond1
                timefreq_cond2_final = timefreq_cond2

            else:
                power_cond1_final = np.concatenate((power_cond1_final, power_cond1))
                power_cond2_final = np.concatenate((power_cond2_final, power_cond2))
                timefreq_cond1_final = np.concatenate((timefreq_cond1_final, timefreq_cond1))
                timefreq_cond2_final = np.concatenate((timefreq_cond2_final, timefreq_cond2))

        self.info2.emit("Computing statistics")

        print(np.shape(power_cond1_final))
        print(np.shape(power_cond2_final))

        fres = float(self.extractDict["FreqRes"])

        # Statistical Analysis
        freqs_array = np.arange(0, n_bins, fres)

        Rsquare, signTab = Compute_Rsquare_Map(power_cond2_final[:, :, :(n_bins - 1)],
                                               power_cond1_final[:, :, :(n_bins - 1)])

        print(electrodeList)
        # Reordering for R map and topography...
        if self.parameterDict["sensorMontage"] == "standard_1020" \
            or self.parameterDict["sensorMontage"] == "biosemi64":
            Rsquare_2, signTab_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_plusplus(Rsquare, signTab, electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)
        elif self.parameterDict["sensorMontage"] == "custom" \
            and self.parameterDict["customMontagePath"] != "":
            Rsquare_2, signTab_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_custom_plus(Rsquare, signTab, self.parameterDict["customMontagePath"], electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)

        # Fill result structure...
        self.Features.electrodes_orig = electrodeList
        self.Features.power_cond2 = power_cond2_2
        self.Features.power_cond1 = power_cond1_2
        self.Features.timefreq_cond1 = timefreq_cond1_2
        self.Features.timefreq_cond2 = timefreq_cond2_2
        # self.Features.time_array = timeVectAtomic  # time-freq map to add later
        self.Features.freqs_array = freqs_array
        self.Features.fres = fres
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsquare = Rsquare_2
        self.Features.Rsign_tab = signTab_2

        self.Features.samplingFreq = self.samplingFreq

        self.stop = True
        self.over.emit(True, "", validFiles)

    def stopThread(self):
        self.stop = True

class TrainClassifier_Timeflux(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, int, str)

    def __init__(self, scenFile, signalFiles, workspaceFolder,
                 parameterDict, currentSessionId, filter_list,
                 cv, currentAttempt, attemptId,
                 model_path, parent=None):

        super().__init__(parent)
        self.stop = False
        self.scenFile = scenFile
        self.signalFiles = signalFiles
        self.workspaceFolder = workspaceFolder
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = currentSessionId
        self.extractDict = parameterDict["Sessions"][currentSessionId]["ExtractionParams"].copy()
        self.filter_list = filter_list
        self.cv = cv
        self.model_path = model_path
        self.currentAttempt = currentAttempt
        self.attemptId = attemptId

    def run(self):

        list_class_1 = []
        list_class_2 = []

        # create the list of file names
        for selectedFilesForViz in self.signalFiles:
            pipelineLabel = "SPECTRUM"
            class1label = self.parameterDict["AcquisitionParams"]["Class1"]
            class2label = self.parameterDict["AcquisitionParams"]["Class2"]
            selectedBasename = selectedFilesForViz
            path1 = os.path.join(self.workspaceFolder, "sessions", f"{self.currentSessionId}", "extract", str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self.workspaceFolder, "sessions", f"{self.currentSessionId}", "extract", str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))
            list_class_1.append(path1)
            list_class_2.append(path2)
        
        print(list_class_1)
        print(list_class_2)
        
        # Find the path for the scenario yaml file
        train_yaml_file_path = os.path.join(self.workspaceFolder, self.scenFile)
        # Change parameters for the yaml File
        update_filenames(
            train_yaml_file_path,
            list_class_1,
            list_class_2,
            self.filter_list,
            self.model_path,
            self.cv,

        )

        # Launch timeflux scenario !
        p = subprocess.Popen([ "timeflux", "-d", str(train_yaml_file_path)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)  # add cwd if needed

        # Print console output, and detect Errors and end of process...
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "ValueError:" in str(output):
                    self.over.emit(False, self.attemptId, output.decode('utf-8').strip())
                if "accuracy" in str(output):
                    classification_scores= str(output)
                if "specificity" in str(output):
                    specificity_scores= str(output)
                if "sensitivity" in str(output):
                    sensitivity_scores= str(output)
                if "Terminated" in str(output):
                    p.kill()
                    break
        
        # Write the message at the end of training
        # Accuracy
        # Split the string by spaces and get the last element, which is the number
        number_str = classification_scores.split()[-1]
        number_sens = specificity_scores.split()[-1]
        number_spe = sensitivity_scores.split()[-1]
        # Extract the float number using regex
        match = re.search(r"[-+]?\d*\.\d+|\d+", number_str)
        if match:
            number = float(match.group(0))
            print(number)
        else:
            print("No number found")
        number = round(number, 3)
        # Extract the sensitivity
        match_sens = re.search(r"[-+]?\d*\.\d+|\d+", number_sens)
        if match_sens:
            number_sens = float(match_sens.group(0))
            number_sens = round(number_sens, 3)
            print(f"Sensitivity score: {number_sens}")
        else:
            print("No sensitivity score found")

        # Extract the specificity
        match_spe = re.search(r"[-+]?\d*\.\d+|\d+", number_spe)
        if match_spe:
            number_spe = float(match_spe.group(0))
            number_spe = round(number_spe, 3)
            print(f"Specificity score: {number_spe}")
        else:
            print("No specificity score found")

        self.currentAttempt["Score"]=number
        # PREPARE GOODBYE MESSAGE...
        textFeats = str("")
        for i in range(len(self.signalFiles)):
            textFeats += str(os.path.basename(self.signalFiles[i]) + "\n")

        textFeats += str("\nFeature(s) ")
        textFeats += str("(" + self.parameterDict["pipelineType"] + "):\n")
        for i in range(len(self.filter_list)):
            textFeats += str(
                "\t" + "Channel " + str(self.filter_list[i][0]) + " at " + str(self.filter_list[i][1]) + " Hz\n")

        textDisplay = textFeats
        textDisplay += str("\n" + "Classification accuracy is :   " + str(number))
        textDisplay += str("\n" + "Classification specificity is :   " + str(number_spe))
        textDisplay += str("\n" + "Classification sensitivity is :   " + str(number_sens))


        self.info.emit(True)    # send "info" signal to increment progressbar
        tstop = time.perf_counter()

        self.stop = True
        self.over.emit(True, self.attemptId, textDisplay)

    def stopThread(self):
        self.stop = True

class UseClassifier_Timeflux(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

    def __init__(self, scenFile, workspaceFolder,
                 parameterDict, currentSessionId,
                 filter_list, model_file_path, parent=None):

        super().__init__(parent)
        self.stop = False
        self.scenFile = scenFile
        self.workspaceFolder = workspaceFolder
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = currentSessionId
        self.extractDict = parameterDict["Sessions"][currentSessionId]["ExtractionParams"].copy()
        self.filter_list = filter_list
        self.model_file_path = model_file_path

    def run(self):

        # Find the path for the scenario yaml file
        classify_yaml_file_path=os.path.join(self.workspaceFolder,self.scenFile)
        print("the path we are checking",classify_yaml_file_path)

        # Change parameters for the yaml File
        update_online_scenario(
            classify_yaml_file_path,
            rate=1,
            keys=self.filter_list,
            epoch_params={'before': self.extractDict["StimulationDelay"], 'after': self.extractDict["StimulationEpoch"]},
            trim_samples=self.extractDict["trim_samples"],
            welch_rate=self.extractDict["PsdSize"],
            path=self.model_file_path,
            nfft=self.extractDict["nfft"]
        )


        # Launch timeflux scenario !
        p = subprocess.Popen([ "timeflux", "-d", str(classify_yaml_file_path)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)  # add cwd if needed

        # Print console output, and detect Errors and end of process...
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "Terminated" in str(output):
                    p.kill()
                    break
        
        self.info.emit(True)    # send "info" signal to increment progressbar
        tstop = time.perf_counter()

        self.stop = True
        self.over.emit(True)

    def stopThread(self):
        self.stop = True
