import sys
import os
import time
import subprocess
import platform
from shutil import copyfile
from importlib import resources

from PySide2 import QtCore
from PySide2.QtCore import Signal
from happyfeat.timeflux.modifyYamFile import modify_Edf_Reader_yaml, modify_extraction_yaml,modify_extraction_yaml_new,update_filenames
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

class Acquisition(QtCore.QThread):
    over = Signal(bool, str)

    def __init__(self, ovScript, scenFile, parameterDict, parent=None):
        super().__init__(parent)
        self.stop = False
        self.ovScript = ovScript
        self.scenFile = scenFile
        self.parameterDict = parameterDict.copy()

    def run(self):
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        exitText = ""
        success = True
        p = subprocess.Popen([command, "--no-gui", "--play", self.scenFile],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # Print console output, and detect end of process...
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "Application terminated" in str(output):
                    break
                if "Could not connect to server" in str(output):
                    exitText = str("Error running \"Acquisition\" scenario\n")
                    exitText += str("Make sure the Acquisition Server is running and in \"Play\" mode\n")
                    success = False
                    break

        self.stop = True
        self.over.emit(success, exitText) #signal emitted by the instance Qthread

    def stopThread(self):
        self.stop = True

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
            electrodeList,sampFreq = generateMetadata_timeflux(os.path.join(self.signalFolder,signalFile))
            # Check everything went ok...
            if not sampFreq:
                errMsg = str("Error while loading metadata CSV file for session " + signalFile)
                self.over.emit(False, errMsg)
                return

            ## MODIFY THE EXTRACTION SCENARIO with entered parameters
            self.extractDict["ChannelNames"] = electrodeList
            self.extractDict["PsdSize"] =  sampFreq
 


            # Modify extraction scenario to use provided signal file, and rename outputs accordingly
            filename = signalFile.removesuffix(".edf")
            outputSpect = str(filename + "-SPECTRUM-" )
            csv_file_path=os.path.join(os.path.split(self.signalFolder)[0],"sessions",self.currentSessionId,"extract")
            reader_yaml_file_path=os.path.join(os.path.split(self.signalFolder)[0],"EDF_Reader_oneshot.yaml")
            extraction_yaml_file_path=os.path.join(os.path.split(self.signalFolder)[0],self.scenFile)
           
            # TODO : need to check what are these baselines for?

            # Example usage:
            # modify_Edf_Reader_yaml(reader_yaml_file_path,os.path.join(self.signalFolder,signalFile))
            # Example usage:
            modify_extraction_yaml_new(
                extraction_yaml_file_path,
                filename=os.path.join(self.signalFolder,signalFile),
                rate=1,
                keys=self.extractDict["ChannelNames"],
                epoch_params={'before': self.extractDict["StimulationDelay"], 'after': self.extractDict["StimulationEpoch"]},
                trim_samples=self.extractDict["trim_samples"],
                welch_rate=self.extractDict["PsdSize"],
                band_ranges={'range_A': self.extractDict["range_A"], 'range_B':self.extractDict["range_B"]},
                recorder_filename=outputSpect,
                path=csv_file_path,
                nfft=self.extractDict["nfft"]
            )

            # Launch timeflux scenario !
            # p = subprocess.Popen([ "timeflux", "-d", str(extraction_yaml_file_path)],
            #                      stdin=subprocess.PIPE, stdout=subprocess.PIPE) # add cwd if needed

            p = subprocess.Popen([ "python", "-m", "timeflux.helpers.handler", "launch", "timeflux", "-d", str(extraction_yaml_file_path)],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE) # add cwd if needed

            # Print console output, and detect end of process...
            while True:
                output = p.stdout.readline()
                if p.poll() is not None:
                    break
                if output:
                    print(str(output))
                    if "Terminating" in str(output):
                        p.terminate()
                        terminate_p = subprocess.Popen(
                        ["python", "-m", "timeflux.helpers.handler", "terminate"],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        terminate_p.communicate() 

                        break

            self.info.emit(True)    # send "info" signal to increment progressbar
            tstop = time.perf_counter()
            print("= Extraction from file " + filename + " finished in " + str(tstop-tstart))

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True
# Get POWER SPECTRUM data from a CSV, generated by the "extraction" part of the software
def Extract_CSV_Data_Timeflux(data_cond, trialLength, nbElectrodes, bins, winlen, shift):

    length=1
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


        self.dataNp1 = []
        self.dataNp2 = []



    def run(self):

        listSampFreq = []
        listElectrodeList = []
        listFreqBins = []
        idxFile = 0

        self.useBaselineFiles = self.parameterDict["pipelineType"] == optionKeys[1]

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
        trialLength = float(self.extractDict["StimulationEpoch"])
        trials = int(self.parameterDict["AcquisitionParams"]["TrialNb"])
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqBins[0]
        winLen = float(self.extractDict["TimeWindowLength"])
        winShift = float(self.extractDict["TimeWindowShift"])

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
                Extract_CSV_Data_Timeflux(self.dataNp1[run], trialLength, nbElectrodes, n_bins, winLen, winShift)
            power_cond2, timefreq_cond2 = \
                Extract_CSV_Data_Timeflux(self.dataNp2[run], trialLength, nbElectrodes, n_bins, winLen, winShift)


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

        trialLengthSec = float(self.parameterDict["AcquisitionParams"]["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        windowLength = float(self.extractDict["TimeWindowLength"])
        windowShift = float(self.extractDict["TimeWindowShift"])
        segmentsPerTrial = round((trialLength - windowLength) / windowShift)
        fres = float(self.extractDict["FreqRes"])

        timeVectAtomic = [0]
        for i in range(segmentsPerTrial - 1):
            timeVectAtomic.append((i + 1) * windowShift)

        timeVectAtomic = np.array(timeVectAtomic)
        time_array = np.empty(0)
        idxTrial = 0
        for trial in range(totalTrials):
            time_array = np.concatenate((time_array, timeVectAtomic + (idxTrial * trialLengthSec)))
            idxTrial += 1

        # Statistical Analysis
        freqs_array = np.arange(0, n_bins, fres)

        Rsigned = Compute_Rsquare_Map(power_cond2_final[:, :, :(n_bins - 1)],
                                      power_cond1_final[:, :, :(n_bins - 1)])

        # Reordering for R map and topography...
        if self.parameterDict["sensorMontage"] == "standard_1020" \
            or self.parameterDict["sensorMontage"] == "biosemi64":
            Rsigned_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_plusplus(Rsigned, electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)
        elif self.parameterDict["sensorMontage"] == "custom" \
            and self.parameterDict["customMontagePath"] != "":
            Rsigned_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_custom_plus(Rsigned, self.parameterDict["customMontagePath"], electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)

        # Fill result structure...
        self.Features.electrodes_orig = electrodeList
        self.Features.power_cond2 = power_cond2_2
        self.Features.power_cond1 = power_cond1_2
        self.Features.timefreq_cond1 = timefreq_cond1_2
        self.Features.timefreq_cond2 = timefreq_cond2_2
        # self.Features.time_array = time_array
        self.Features.time_array = timeVectAtomic
        self.Features.freqs_array = freqs_array
        self.Features.fres = fres
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsigned = Rsigned_2



        self.Features.samplingFreq = self.samplingFreq

        self.stop = True
        self.over.emit(True, "", validFiles)

    def stopThread(self):
        self.stop = True




class TrainClassifier(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

    def __init__(self, scenFile, signalFiles, workspaceFolder,
                 parameterDict, currentSessionId,filter_list, parent=None):

        super().__init__(parent)
        self.stop = False
        self.scenFile = scenFile
        self.signalFiles = signalFiles
        self.workspaceFolder = workspaceFolder
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = currentSessionId
        self.extractDict = parameterDict["Sessions"][currentSessionId]["ExtractionParams"].copy()
        self.filter_list=filter_list
    def run(self):

        list_class_1=[]
        list_class_2=[]

        # cretae the list of file names
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
        
        train_yaml_file_path=os.path.join(self.workspaceFolder,self.scenFile)

        update_filenames(
            train_yaml_file_path,
            list_class_1,
            list_class_2,
            self.filter_list

        )

        # Launch timeflux scenario !
        p = subprocess.Popen([ "timeflux", "-d", str(train_yaml_file_path)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE) # add cwd if needed

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

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True

class RunClassifier(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

    def __init__(self, classifFiles, templateFolder,
                 workspaceFolder, ovScript,
                 classifWeightsPath,
                 listFeat, listFeat2,
                 parameterDict, sampFreq, electrodeList,
                 shouldRun, isOnline, parent=None):

        super().__init__(parent)
        self.stop = False
        self.classifFiles = classifFiles
        self.templateFolder = templateFolder
        self.workspaceFolder = workspaceFolder
        self.ovScript = ovScript
        self.listFeat = listFeat
        self.listFeat2 = listFeat2
        self.classifWeightsPath = classifWeightsPath
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = self.parameterDict["currentSessionId"]
        self.extractDict = parameterDict["Sessions"][self.parameterDict["currentSessionId"]]["ExtractionParams"].copy()
        self.samplingFreq = sampFreq
        self.electrodeList = electrodeList
        self.shouldRun = shouldRun
        self.isOnline = isOnline
        self.exitText = ""

        self.usingDualFeatures = False
        if self.parameterDict["pipelineType"] == optionKeys[3] \
                or self.parameterDict["pipelineType"] == optionKeys[4]:
            self.usingDualFeatures = True

    def run(self):

        selectedFeats = None
        selectedFeats2 = None
        if not self.usingDualFeatures:
            selectedFeats, errMsg = self.checkSelectedFeats(self.listFeat, self.samplingFreq, self.electrodeList)
            if not selectedFeats:
                self.over.emit(False, errMsg)
                return
        else:
            selectedFeats, errMsg = self.checkSelectedFeats(self.listFeat, self.samplingFreq, self.electrodeList)
            if not selectedFeats:
                self.over.emit(False, errMsg)
                return
            selectedFeats2, errMsg = self.checkSelectedFeats(self.listFeat2, self.samplingFreq, self.electrodeList)
            if not selectedFeats2:
                self.over.emit(False, errMsg)
                return

        # Computing the "Epoch Average" count, important in the classification scenario.
        epochCount = [0, 0]
        stimEpochLength = float(self.extractDict["StimulationEpoch"])
        if self.parameterDict["pipelineType"] == optionKeys[1]:
            winLength = float(self.extractDict["TimeWindowLength"])
            winShift = float(self.extractDict["TimeWindowShift"])
            epochCount[0] = np.floor((stimEpochLength - winLength) / winShift) + 1
        elif self.parameterDict["pipelineType"] == optionKeys[2]:
            winLength = float(self.extractDict["ConnectivityLength"])
            overlap = float(self.extractDict["ConnectivityOverlap"])
            winShift = winLength * (100.0-overlap) / 100.0
            epochCount[0] = np.floor((stimEpochLength - winLength) / winShift) + 1
        elif self.parameterDict["pipelineType"] == optionKeys[3] \
                or self.parameterDict["pipelineType"] == optionKeys[4]:
            winLength0 = float(self.extractDict["TimeWindowLength"])
            winShift0 = float(self.extractDict["TimeWindowShift"])
            epochCount[0] = np.floor((stimEpochLength - winLength0) / winShift0) + 1
            winLength1 = float(self.extractDict["ConnectivityLength"])
            overlap = float(self.extractDict["ConnectivityOverlap"])
            winShift1 = winLength1 * (100.0-overlap) / 100.0
            epochCount[1] = np.floor((stimEpochLength - winLength1) / winShift1) + 1

        ## MODIFY THE SCENARIO with entered parameters
        # /!\ after updating ARburg order and FFT size using sampfreq
        self.extractDict["ChannelNames"] = ";".join(self.electrodeList)
        self.extractDict["AutoRegressiveOrder"] = str(
            timeToSamples(float(self.extractDict["AutoRegressiveOrderTime"]), self.samplingFreq))
        self.extractDict["PsdSize"] = str(freqResToPsdSize(float(self.extractDict["FreqRes"]), self.samplingFreq))

        # Special case : "connectivity shift", used in scenarios but not set that way in the interface
        if "ConnectivityOverlap" in self.extractDict.keys():
            self.extractDict["ConnectivityShift"] = str(float(self.extractDict["ConnectivityLength"]) * (100.0 - float(self.extractDict["ConnectivityOverlap"])) / 100.0)

        # Select relevant scenario (in bcipipeline_settings.py)
        if self.isOnline:
            scenIdx = 3  # idx in bcipipeline_settings.py
            scenName = templateScenFilenames[scenIdx]
        else:
            scenIdx = 6  # idx in bcipipeline_settings.py
            scenName = templateScenFilenames[scenIdx]

        destScenFile = os.path.join(self.workspaceFolder, scenName)

        # COPY SCENARIO FROM TEMPLATE, SO THE USER CAN DO THIS MULTIPLE TIMES
        print("---Copying file from folder " + str(__name__.split('.')[0] + '.' + self.templateFolder))
        with resources.path(str(__name__.split('.')[0] + '.' + self.templateFolder), scenName) as srcFile:
            print("---Copying file " + str(srcFile) + " to " + str(destScenFile))
            copyfile(srcFile, destScenFile)

        # current session (linked to extraction parameters), to know where to get training results...
        trainingpath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train")
        modifyScenarioGeneralSettings(str(destScenFile), self.extractDict)

        # modify online or replay scenario with selected features
        if not self.usingDualFeatures:
            modifyTrainScenUsingSplitAndClassifiers("SPLIT", "Classifier processor", selectedFeats, epochCount[0], destScenFile)
            # Special case: "connectivity metric"
            if "ConnectivityMetric" in self.extractDict.keys():
                modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destScenFile)
        else:
            modifyTrainScenUsingSplitAndClassifiers("SPLIT POWSPECTRUM", "Classifier processor", selectedFeats, epochCount[0], destScenFile)
            modifyTrainScenUsingSplitAndClassifiers("SPLIT CONNECT", "Classifier processor", selectedFeats2, epochCount[1], destScenFile)
            modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destScenFile)

        modifyOneGeneralSetting(destScenFile, "ClassifWeights", self.classifWeightsPath)

        if not self.shouldRun:
            # WE STOP HERE!
            textOut = "Scenario sc3-online.xml has been updated with the following:\n"
            textOut += "\t- Using " + self.classifWeightsPath + "\n"

            if not self.usingDualFeatures:
                textOut += str("\n\t- Feature(s) ")
                textOut += str("(" + self.parameterDict["pipelineType"] + "):\n")
                for i in range(len(selectedFeats)):
                    textOut += str(
                        "\t\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
            else:
                textOut += str("\n\t- Feature(s) for PowSpectrum:\n")
                for i in range(len(selectedFeats)):
                    textOut += str(
                        "\t\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
                textOut += str("\n\t- Feature(s) for Connectivity:\n")
                for i in range(len(selectedFeats2)):
                    textOut += str(
                        "\t\t" + "Channel " + str(selectedFeats2[i][0]) + " at " + str(selectedFeats2[i][1]) + " Hz\n")

            self.exitText = textOut
            self.stop = True
            self.over.emit(True, self.exitText)
            return

        # END SC3
        #---------------------
        # OTHERWISE... SC4

        # Get electrodes lists and sampling freqs, and check that they match
        # + that the selected channels are in the list of electrodes
        classifSigFiles = []
        listSampFreq = []
        listElectrodeList = []
        for classifFile in self.classifFiles:
            generateMetadata(classifFile, self.ovScript)
            metaFile = classifFile.replace(".ov", "-META.csv")
            sampFreqTemp, electrodeListTemp = extractMetadata(metaFile)

            listSampFreq.append(sampFreqTemp)
            listElectrodeList.append(electrodeListTemp)
            classifSigFiles.append(classifFile)  # ??

        if not all(freqsamp == self.samplingFreq for freqsamp in listSampFreq):
            errMsg = str("Error when loading signal files for classification\n")
            errMsg = str(
                errMsg + "Sampling frequency mismatch (expected " + str(self.samplingFreq) + ", got " + str(
                    listSampFreq) + ")")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        for electrodeList in listElectrodeList:
            if not set(electrodeList) == set(self.electrodeList):
                errMsg = str("Error when loading signal files for classification\n")
                errMsg = str(errMsg + "Electrode List mismatch")
                self.over.emit(False, errMsg)
                return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))


        targetList = []
        classifiedList = []
        fileIdx = 1

        # RUN REPLAY SCENARIO ON EVERY SIGNAL FILE
        for sigFile in classifSigFiles:
            # increment progressbars
            self.info.emit(True)
            self.info2.emit("Running Scenario on file" +  str(fileIdx) +"/" + str(len(classifSigFiles)))

            # change scenario IO
            modifyOneGeneralSetting(destScenFile, "EEGData", sigFile)
            success, targetListTemp, classifiedListTemp = self.playClassifierScenario(destScenFile)
            targetList.extend(targetListTemp)
            classifiedList.extend(classifiedListTemp)

            if not success:
                self.errorMessageRunner()
                self.over.emit(False, self.exitText)

        # PREPARE RESULTS & GOODBYE MESSAGE...

        # count nb of differences in both (ordered) lists
        nbClassifs = len(targetList)
        nbErrors = sum(map(lambda x, y: bool(x - y), targetList, classifiedList))
        accuracy = 100.0 * float((nbClassifs - nbErrors) / nbClassifs)

        tp1 = 0
        fn1 = 0
        tp2 = 0
        fn2 = 0
        for idx in range(len(targetList)):
            if targetList[idx] == classifiedList[idx]:
                if targetList[idx] == 1:
                    tp1 += 1
                else:
                    tp2 += 1
            else:
                if targetList[idx] == 1:
                    fn1 += 1
                else:
                    fn2 += 1

        precision1 = 100.0*float(tp1 / (tp1 + fn1))
        precision2 = 100.0*float(tp2 / (tp2 + fn2))

        messageClassif = "Overall accuracy : " + str(accuracy) + "% (" + str(nbClassifs) + " trials)\n"
        messageClassif += "\tClass 1 (" + self.parameterDict["AcquisitionParams"]["Class1"] + ")| Precision  : " + str(precision1) + "% (" + str(tp1+fn1) + " trials)\n"
        messageClassif += "\tClass 2 (" + self.parameterDict["AcquisitionParams"]["Class2"] + ")| Precision  : " + str(precision2) + "% (" + str(tp2+fn2) + " trials)\n"

        # PREPARE DISPLAYED MESSAGE...
        textFeats = str("======CLASSIFICATION ATTEMPT=======\n")
        textFeats += str("Signal Files\n")
        for i in range(len(classifSigFiles)):
            textFeats += str("\t" + os.path.basename(classifSigFiles[i]) + "\n")

        if not self.usingDualFeatures:
            textFeats += str("\nFeature(s) ")
            textFeats += str("(" + self.parameterDict["pipelineType"]+"):\n")
            for i in range(len(selectedFeats)):
                textFeats += str("\t"+"Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
        else:
            textFeats += str("\nFeature(s) for PowSpectrum:\n")
            for i in range(len(selectedFeats)):
                textFeats += str(
                    "\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
            textFeats += str("Feature(s) for Connectivity:\n")
            for i in range(len(selectedFeats2)):
                textFeats += str(
                    "\t" + "Channel " + str(selectedFeats2[i][0]) + " at " + str(selectedFeats2[i][1]) + " Hz\n")

        textDisplay = textFeats
        textDisplay += str("\n" + messageClassif)

        self.exitText = textDisplay


        self.stop = True
        self.over.emit(True, self.exitText)

    def stopThread(self):
        self.stop = True

    def errorMessageRunner(self):
        textError = str("Error running \"Run/Replay\" scenario\n")
        self.exitText = textError

    def checkSelectedFeats(self, inputSelectedFeats, sampFreq, electrodeList):
        selectedFeats = []
        errMsg = ""
        # Checks :
        # - No empty field
        # - frequencies in acceptable ranges
        # - channels in list
        n_bins = int((sampFreq / 2) + 1)
        for idx, feat in enumerate(inputSelectedFeats):
            if feat == "":
                errMsg = str("Pair " + str(idx + 1) + " is empty...")
                return None, errMsg
            [chan, freqstr] = feat.split(";")
            if chan not in electrodeList:
                errMsg = str("Channel in pair " + str(idx + 1) + " (" + str(chan) + ") is not in the list...")
                return None, errMsg
            freqs = freqstr.split(":")
            for freq in freqs:
                if not freq.isdigit():
                    errMsg = str("Frequency in pair " + str(idx + 1) + " (" + str(
                        freq) + ") has an invalid format, must be an integer...")
                    return None, errMsg
                if int(freq) >= n_bins:
                    errMsg = str(
                        "Frequency in pair " + str(idx + 1) + " (" + str(freq) + ") is not in the acceptable range...")
                    return None, errMsg
            selectedFeats.append(feat.split(";"))
            print(feat)

        return selectedFeats, errMsg

    def playClassifierScenario(self, scenFile):
        # ----------
        # Run the provided run/replay scenario, and check the console output for termination, errors, and
        # classification results
        # ----------

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # Run actual command (openvibe-designer.cmd --no-gui --play-fast <scen.xml>)
        p = subprocess.Popen([command, "--invisible", "--play-fast", scenFile],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # Read console output to detect end of process
        # and prompt user with classification score. Quite artisanal but works
        success = True
        classifierOutputStr = ""
        targetList = []
        classifiedList = []
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "Invalid indexes: stopIdx - trainIndex = 1" in str(output):
                    success = False
                    return success, None, None
                if "Application terminated" in str(output):
                    break

                if "aka Target" in str(output):
                    if "769[OVTK_GDF_Left]" in str(output):
                        targetList.append(1)
                    elif "770[OVTK_GDF_Right]" in str(output):
                        targetList.append(2)
                if "aka Classified" in str(output):
                    if "769[OVTK_GDF_Left]" in str(output):
                        classifiedList.append(1)
                    elif "770[OVTK_GDF_Right]" in str(output):
                        classifiedList.append(2)

        return success, targetList, classifiedList
