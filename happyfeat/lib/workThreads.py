import sys
import os
import time
import subprocess
import platform
from shutil import copyfile
from importlib import resources

from PySide6 import QtCore
from PySide6.QtCore import Signal

from happyfeat.lib.mergeRunsCsv import mergeRunsCsv, mergeRunsCsv_new
from happyfeat.lib.extractMetaData import extractMetadata, generateMetadata
from happyfeat.lib.modifyOpenvibeScen import *
from happyfeat.lib.Visualization_Data import *
from happyfeat.lib.featureExtractUtils import *
from happyfeat.lib.utils import *

from happyfeat.lib.bcipipeline_settings import *

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
        self.over.emit(success, exitText)

    def stopThread(self):
        self.stop = True

class Extraction(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

    def __init__(self, ovScript, scenFile, signalFiles, signalFolder,
                 parameterDict, currentSessionId, parent=None):

        super().__init__(parent)
        self.stop = False
        self.ovScript = ovScript
        self.scenFile = scenFile
        self.signalFiles = signalFiles
        self.signalFolder = signalFolder
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = currentSessionId
        self.extractDict = parameterDict["Sessions"][currentSessionId]["ExtractionParams"].copy()

    def run(self):
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        for signalFile in self.signalFiles:
            tstart = time.perf_counter()

            self.info2.emit(str("Extracting data for file " + signalFile + "..."))

            # Verify the existence of metadata files for each selected files,
            # and if not, generate them.
            # Then extract sampling frequency and electrode list
            sampFreq = None
            electrodeList = None
            metaFile = signalFile.replace(".ov", "-META.csv")

            if metaFile in os.listdir(self.signalFolder):
                sampFreq, electrodeList = extractMetadata(os.path.join(self.signalFolder, metaFile))
            else:
                generateMetadata(os.path.join(self.signalFolder, signalFile), self.ovScript)
                sampFreq, electrodeList = extractMetadata(os.path.join(self.signalFolder, metaFile))
            # Check everything went ok...
            if not sampFreq:
                errMsg = str("Error while loading metadata CSV file for session " + signalFile)
                self.over.emit(False, errMsg)
                return

            ## MODIFY THE EXTRACTION SCENARIO with entered parameters
            # /!\ after updating ARburg order and FFT size using sampfreq
            self.extractDict["ChannelNames"] = ";".join(electrodeList)
            self.extractDict["AutoRegressiveOrder"] = str(
                timeToSamples(float(self.extractDict["AutoRegressiveOrderTime"]), sampFreq))
            self.extractDict["PsdSize"] = str(freqResToPsdSize(float(self.extractDict["FreqRes"]), sampFreq))

            # Special case : "subset of electrodes" for connectivity
            # DISABLED FOR NOW
            # if field is empty, use all electrodes
            # if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            #     if self.parameterDict["ChannelSubset"] == "":
            #         self.parameterDict["ChannelSubset"] = self.parameterDict["ChannelNames"]
            self.extractDict["ChannelSubset"] = self.extractDict["ChannelNames"]

            # Special case : "connectivity shift", used in scenarios but not set that way
            # in the interface
            if "ConnectivityOverlap" in self.extractDict.keys():
                self.extractDict["ConnectivityShift"] = str(float(self.extractDict["ConnectivityLength"]) * (100.0 - float(self.extractDict["ConnectivityOverlap"])) / 100.0)

            # Modify the scenario
            modifyScenarioGeneralSettings(self.scenFile, self.extractDict)

            # Special case: "connectivity metric"
            if "ConnectivityMetric" in self.extractDict.keys():
                modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], self.scenFile)

            # Modify extraction scenario to use provided signal file, and rename outputs accordingly
            filename = signalFile.removesuffix(".ov")
            outputSpect1 = str(filename + "-SPECTRUM-" + self.parameterDict["AcquisitionParams"]["Class1"] + ".csv")
            outputSpect2 = str(filename + "-SPECTRUM-" + self.parameterDict["AcquisitionParams"]["Class2"] + ".csv")
            outputConnect1 = str(filename + "-CONNECT-" + self.parameterDict["AcquisitionParams"]["Class1"] + ".csv")
            outputConnect2 = str(filename + "-CONNECT-" + self.parameterDict["AcquisitionParams"]["Class2"] + ".csv")
            outputSpectBaseline1 = str(filename + "-SPECTRUM-" + self.parameterDict["AcquisitionParams"]["Class1"] + "-BASELINE.csv")
            outputSpectBaseline2 = str(filename + "-SPECTRUM-" + self.parameterDict["AcquisitionParams"]["Class2"] + "-BASELINE.csv")
            outputTrials = str(filename + "-TRIALS.csv")
            outputBaseline = str(filename + "-BASELINE.csv")
            modifyExtractionIO(self.scenFile, signalFile,
                               outputSpect1, outputSpect2,
                               outputSpectBaseline1, outputSpectBaseline2,
                               outputConnect1, outputConnect2,
                               outputTrials, outputBaseline,
                               self.currentSessionId)

            # Launch OV scenario !
            p = subprocess.Popen([command, "--invisible", "--play-fast", self.scenFile],
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

            self.info.emit(True)    # send "info" signal to increment progressbar
            tstop = time.perf_counter()
            print("= Extraction from file " + filename + " finished in " + str(tstop-tstart))

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True


class LoadFilesForVizPowSpectrum(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str, list, list, list)

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
        self.dataNp1baseline = []
        self.dataNp2baseline = []

    def run(self):

        listSampFreq = []
        listElectrodeList = []
        listFreqBins = []
        idxFile = 0

        self.useBaselineFiles = self.parameterDict["pipelineType"] == optionKeys[1]

        validFiles = []
        initSizes = []
        validSizes = []
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

            if self.useBaselineFiles:
                path1baseline = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class1label + "-BASELINE.csv"))
                path2baseline = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class2label + "-BASELINE.csv"))
                self.info2.emit(str("Loading " + pipelineLabel + " Baseline Data for file " + str(idxFile) + " : " + selectedFilesForViz))
                [header1baseline, data1baseline] = load_csv_np(path1baseline)
                [header2baseline, data2baseline] = load_csv_np(path2baseline)

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
                self.over.emit(False, errMsg, None, None, None)
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
                self.over.emit(False, errMsg, None, None, None)
                return

            listElectrodeList.append(electrodeList1)

            # check for invalid values...
            initSize1 = 0
            validSize1 = 0
            initSize2 = 0
            validSize2 = 0
            newData1, valid1, initSize1, validSize1 = check_valid_np(data1)
            newData2, valid2, initSize2, validSize2 = check_valid_np(data2)

            if valid1 and valid2:
                validFiles.append(True)
            else:
                validFiles.append(False)

            initSizes.append(initSize1 + initSize2)
            validSizes.append(validSize1 + validSize2)

            self.dataNp1.append(data1)
            self.dataNp2.append(data2)
            if self.useBaselineFiles:
                self.dataNp1baseline.append(data1baseline)
                self.dataNp2baseline.append(data2baseline)
            self.info.emit(True)

        # Check if all files have the same sampling freq and electrode list. If not, for now, we don't process further
        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            self.samplingFreq = listSampFreq[0]
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Electrode List mismatch")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        if not all(freqBins == listFreqBins[0] for freqBins in listFreqBins):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Not same number of frequency bins (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg, None, None, None)
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
        power_cond1_baseline_final = None
        power_cond2_baseline_final = None
        timefreq_cond1_final = None
        timefreq_cond2_final = None
        timefreq_cond1_baseline_final = None
        timefreq_cond2_baseline_final = None
        idxFile = 0
        for run in range(len(self.dataNp1)):
            idxFile += 1
            self.info2.emit(str("Processing data for file " + str(idxFile)))
            power_cond1, timefreq_cond1 = \
                Extract_CSV_Data(self.dataNp1[run], trialLength, nbElectrodes, n_bins, winLen, winShift)
            power_cond2, timefreq_cond2 = \
                Extract_CSV_Data(self.dataNp2[run], trialLength, nbElectrodes, n_bins, winLen, winShift)
            if self.useBaselineFiles:
                power_cond1_baseline, timefreq_cond1_baseline = \
                    Extract_CSV_Data(self.dataNp1baseline[run], trialLength, nbElectrodes, n_bins, winLen, winShift)
                power_cond2_baseline, timefreq_cond2_baseline = \
                    Extract_CSV_Data(self.dataNp2baseline[run], trialLength, nbElectrodes, n_bins, winLen, winShift)

            if power_cond1_final is None:
                power_cond1_final = power_cond1
                power_cond2_final = power_cond2
                timefreq_cond1_final = timefreq_cond1
                timefreq_cond2_final = timefreq_cond2
                if self.useBaselineFiles:
                    power_cond1_baseline_final = power_cond1_baseline
                    power_cond2_baseline_final = power_cond2_baseline
                    timefreq_cond1_baseline_final = timefreq_cond1_baseline
                    timefreq_cond2_baseline_final = timefreq_cond2_baseline
            else:
                power_cond1_final = np.concatenate((power_cond1_final, power_cond1))
                power_cond2_final = np.concatenate((power_cond2_final, power_cond2))
                timefreq_cond1_final = np.concatenate((timefreq_cond1_final, timefreq_cond1))
                timefreq_cond2_final = np.concatenate((timefreq_cond2_final, timefreq_cond2))
                if self.useBaselineFiles:
                    power_cond1_baseline_final = np.concatenate((power_cond1_baseline_final, power_cond1_baseline))
                    power_cond2_baseline_final = np.concatenate((power_cond2_baseline_final, power_cond2_baseline))
                    timefreq_cond1_baseline_final = np.concatenate((timefreq_cond1_baseline_final, timefreq_cond1_baseline))
                    timefreq_cond2_baseline_final = np.concatenate((timefreq_cond2_baseline_final, timefreq_cond2_baseline))

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
        if np.shape(power_cond1_final)[0] == 0 or np.shape(power_cond2_final)[0] == 0:
            errMsg = str("Error when loading power spectrum CSV files\n")
            errMsg = str(errMsg + "Not enough valid trials to proceed...\n")
            errMsg = str(errMsg + "Try again with different runs/signals\n")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            Rsquare, signTab = Compute_Rsquare_Map(power_cond1_final[:, :, :(n_bins - 1)],
                                                   power_cond2_final[:, :, :(n_bins - 1)])

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
        # self.Features.time_array = time_array
        self.Features.time_array = timeVectAtomic
        self.Features.freqs_array = freqs_array
        self.Features.fres = fres
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsquare = Rsquare_2
        self.Features.Rsign_tab = signTab_2

        if self.useBaselineFiles:
            self.Features.average_baseline_cond1 = np.mean(power_cond1_baseline_final, axis=0)
            self.Features.std_baseline_cond1 = np.std(power_cond1_baseline_final, axis=0)
            self.Features.average_baseline_cond2 = np.mean(power_cond2_baseline_final, axis=0)
            self.Features.std_baseline_cond2 = np.std(power_cond2_baseline_final, axis=0)

        self.Features.samplingFreq = self.samplingFreq

        self.stop = True
        self.over.emit(True, "", validFiles, initSizes, validSizes)

    def stopThread(self):
        self.stop = True

# Class for loading extracted data in the "Connectivity Pipeline"
# data are NODE STRENGTH (not raw connectivity matrices), we manage them
# almost like power spectra...
class LoadFilesForVizConnectivity(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str, list, list, list)

    def __init__(self, analysisFiles, workingFolder, metaFolder, parameterDict, Features, sampFreq, parent=None):

        super().__init__(parent)
        self.stop = False
        self.analysisFiles = analysisFiles
        self.workingFolder = workingFolder
        self.metaFolder = metaFolder
        self.parameterDict = parameterDict.copy()
        self.extractDict = parameterDict["Sessions"][parameterDict["currentSessionId"]]["ExtractionParams"].copy()
        self.Features = Features
        self.samplingFreq = sampFreq

        self.dataNp1 = []
        self.dataNp2 = []

    def run(self):

        listSamplingFreqs = []
        listFreqs = []
        listElectrodeList = []
        idxFile = 0

        validFiles = []
        initSizes = []
        validSizes = []
        for selectedFilesForViz in self.analysisFiles:
            idxFile += 1
            pipelineLabel = "CONNECT"
            class1label = self.parameterDict["AcquisitionParams"]["Class1"]
            class2label = self.parameterDict["AcquisitionParams"]["Class2"]
            selectedBasename = selectedFilesForViz

            # First, get metadata...
            metapath = os.path.join(self.metaFolder, str(selectedBasename + "-META.csv"))
            [sampFreq, electrodeList] = extractMetadata(metapath)
            listSamplingFreqs.append(sampFreq)

            # Now load data...
            path1 = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))

            self.info2.emit(str("Loading " + pipelineLabel + " Data for file " + str(idxFile) + " : " + selectedFilesForViz))
            [header1, data1] = load_csv_np(path1)
            [header2, data2] = load_csv_np(path2)

            # Check that files match...!
            # Infos in the columns header of the CSVs in format "Time:500x64"
            # (Column zero contains starting time of the row)
            # 500 is nb of freq bins, 64 is channels)
            freqBins1 = int(header1[0].split(":")[-1].split("x")[0])
            freqBins2 = int(header2[0].split(":")[-1].split("x")[0])
            if freqBins1 != freqBins2:
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "\nfrequency bins mismatch")
                errMsg = str(errMsg + "\n(" + str(freqBins1) + " vs " + str(freqBins2) + ")")
                self.over.emit(False, errMsg, None, None, None)
                return

            listFreqs.append(freqBins1)

            # check match between electrodes...
            nbElec1 = int(header1[0].split(":")[-1].split("x")[1])
            nbElec2 = int(header2[0].split(":")[-1].split("x")[1])
            elecTemp1 = header1[2:nbElec1+2]
            elecTemp2 = header2[2:nbElec2+2]
            electrodeList1 = []
            electrodeList2 = []
            for i in range(0, len(elecTemp1)):
                electrodeList1.append(elecTemp1[i].split(":")[1])
                electrodeList2.append(elecTemp2[i].split(":")[1])

            if electrodeList1 != electrodeList2:
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "\nElectrode List mismatch")
                self.over.emit(False, errMsg, None, None, None)
                return

            listElectrodeList.append(electrodeList1)

            # check that the data is valid, and doesn't contain NaN
            initSize1 = 0
            validSize1 = 0
            initSize2 = 0
            validSize2 = 0
            newData1, valid1, initSize1, validSize1 = check_valid_np(data1)
            newData2, valid2, initSize2, validSize2 = check_valid_np(data2)

            if valid1 and valid2:
                validFiles.append(True)
            else:
                validFiles.append(False)

            initSizes.append(initSize1 + initSize2)
            validSizes.append(validSize1 + validSize2)

            self.dataNp1.append(newData1)
            self.dataNp2.append(newData2)

            self.info.emit(True)

        # Check if all files have the same sampling freq and electrode list. If not, for now, we don't process further
        if not all(nbfreqs == listFreqs[0] for nbfreqs in listFreqs):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "nb of frequency mismatch (" + str(listFreqs) + ")")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            print("Nb of Frequency bins for selected files : " + str(listFreqs[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sensor List mismatch")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        if not all(sampFreq == listSamplingFreqs[0] for sampFreq in listSamplingFreqs):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling Freq mismatch")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.extractDict["StimulationEpoch"])
        trials = int(self.parameterDict["AcquisitionParams"]["TrialNb"])
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqs[0]
        winLen = float(self.extractDict["ConnectivityLength"])
        overlap = float(self.extractDict["ConnectivityOverlap"])
        winShift = winLen * (1.0 - overlap/ 100)
        sampFreq = listSamplingFreqs[0]

        # For multiple runs (ie. multiple selected CSV files), we just concatenate
        # the trials from all files. Then the displayed spectral features (R²map, PSD, topography)
        # will be computed as averages over all the trials.
        connect_cond1_final = None
        connect_cond2_final = None
        timefreq_cond1_final = None
        timefreq_cond2_final = None
        timefreq_cond1_baseline_final = None
        timefreq_cond2_baseline_final = None
        idxFile = 0
        for run in range(len(self.dataNp1)):
            idxFile += 1
            self.info2.emit(str("Processing data for file " + str(idxFile)))
            connect_cond1, timefreq_cond1 = \
                Extract_Connect_NodeStrength_TimeFreq_CSV_Data(self.dataNp1[run], trialLength, nbElectrodes, n_bins,
                                                               winLen, overlap)
            connect_cond2, timefreq_cond2 = \
                Extract_Connect_NodeStrength_TimeFreq_CSV_Data(self.dataNp2[run], trialLength, nbElectrodes, n_bins,
                                                               winLen, overlap)

            # transpose to fit data format with future reordering functions...
            timefreq_cond1_transp = timefreq_cond1.transpose(0, 3, 1, 2)
            timefreq_cond2_transp = timefreq_cond2.transpose(0, 3, 1, 2)

            if connect_cond1_final is None:
                connect_cond1_final = connect_cond1
                connect_cond2_final = connect_cond2

                timefreq_cond1_final = timefreq_cond1_transp
                timefreq_cond2_final = timefreq_cond2_transp

            else:
                connect_cond1_final = np.concatenate((connect_cond1_final, connect_cond1))
                connect_cond2_final = np.concatenate((connect_cond2_final, connect_cond2))

                timefreq_cond1_final = np.concatenate((timefreq_cond1_final, timefreq_cond1_transp))
                timefreq_cond2_final = np.concatenate((timefreq_cond2_final, timefreq_cond2_transp))

        self.info2.emit("Computing statistics")
        trialLengthSec = float(self.parameterDict["AcquisitionParams"]["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        fres = float(self.extractDict["FreqRes"])

        # Statistical Analysis...
        freqs_array = np.arange(0, n_bins, fres)
        if np.shape(connect_cond1_final)[0] == 0 or np.shape(connect_cond2_final)[0] == 0:
            errMsg = str("Error when loading connectivity CSV files\n")
            errMsg = str(errMsg + "Not enough valid trials to proceed...\n")
            errMsg = str(errMsg + "Try again with different runs/signals\n")
            self.over.emit(False, errMsg, None, None, None)
            return
        else:
            Rsquare, signTab = Compute_Rsquare_Map(connect_cond1_final[:, :, :(n_bins - 1)],
                                                   connect_cond2_final[:, :, :(n_bins - 1)])

        # Reordering for R map and topography...
        if self.parameterDict["sensorMontage"] == "standard_1020" \
                or self.parameterDict["sensorMontage"] == "biosemi64":
            Rsquare_2, signTab_2, electrodes_final, connect_cond1_2, connect_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_plusplus(Rsquare, signTab, electrodeList, connect_cond1_final, connect_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)
        elif self.parameterDict["sensorMontage"] == "custom" \
                and self.parameterDict["customMontagePath"] != "":
            Rsquare_2, signTab_2, electrodes_final, connect_cond1_2, connect_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_custom_plus(Rsquare, signTab, self.parameterDict["customMontagePath"],
                                      electrodeList, connect_cond1_final, connect_cond2_final,
                                      timefreq_cond1_final, timefreq_cond2_final)

        # Fill Features struct...
        self.Features.electrodes_orig = electrodeList
        self.Features.electrodes_final = electrodes_final
        self.Features.power_cond1 = connect_cond1_2
        self.Features.power_cond2 = connect_cond2_2
        self.Features.timefreq_cond1 = timefreq_cond1_2
        self.Features.timefreq_cond2 = timefreq_cond2_2
        self.Features.fres = fres
        self.Features.samplingFreq = sampFreq
        self.Features.freqs_array = freqs_array

        self.Features.Rsquare = Rsquare_2
        self.Features.Rsign_tab = signTab_2

        self.stop = True
        self.over.emit(True, "", validFiles, initSizes, validSizes)

    def stopThread(self):
        self.stop = True


class TrainClassifier(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, int, str)

    def __init__(self, trainingFiles,
                 signalFolder, templateFolder,
                 workspaceFolder, ovScript,
                 trainingSize, selectedFeats,
                 parameterDict, sampFreq, currentAttempt, attemptId,
                 speedUp, parent=None):

        super().__init__(parent)
        self.stop = False
        self.trainingFiles = trainingFiles
        self.signalFolder = signalFolder
        self.templateFolder = templateFolder
        self.workspaceFolder = workspaceFolder
        self.ovScript = ovScript
        self.trainingSize = trainingSize
        self.currentAttempt = currentAttempt
        self.attemptId = attemptId
        self.speedUp = speedUp

        # selectedFeats is either a list of feats. of interest
        # or (case of mixed features) a list of 2 lists
        self.selectedFeats = selectedFeats.copy()
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = self.parameterDict["currentSessionId"]
        self.extractDict = parameterDict["Sessions"][self.parameterDict["currentSessionId"]]["ExtractionParams"].copy()
        self.freqRes = float(self.extractDict["FreqRes"])
        self.samplingFreq = sampFreq
        self.exitText = ""

        self.usingDualFeatures = False
        if self.parameterDict["pipelineType"] == optionKeys[3] \
            or self.parameterDict["pipelineType"] == optionKeys[4]:
            self.usingDualFeatures = True

    def run(self):
        # Get electrodes lists and sampling freqs, and check that they match
        # + that the selected channels are in the list of electrodes
        trainingSigList = []
        listSampFreq = []
        listElectrodeList = []
        for trainingFile in self.trainingFiles:
            path = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", trainingFile)
            header = pd.read_csv(path, nrows=0).columns.tolist()
            listSampFreq.append(int(header[0].split(':')[1].removesuffix('Hz')))
            listElectrodeList.append(header[2:-3])
            trainingSigList.append(path)

            if self.parameterDict["pipelineType"] == optionKeys[4]:
                baselineFile = trainingFile.replace('TRIALS', 'BASELINE')
                path = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", baselineFile)
                header = pd.read_csv(path, nrows=0).columns.tolist()
                listSampFreq.append(int(header[0].split(':')[1].removesuffix('Hz')))
                listElectrodeList.append(header[2:-3])
                trainingSigList.append(path)

        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            self.over.emit(False, self.attemptId, errMsg)
            return
        else:
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Electrode List mismatch")
            self.over.emit(False, self.attemptId, errMsg)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        # Get the features selected for training, and check if their values are correct
        selectedFeats = None
        selectedFeats2 = None
        if not self.usingDualFeatures:
            selectedFeats, errMsg = self.checkSelectedFeats(self.selectedFeats, listSampFreq[0], listElectrodeList[0])
            if not selectedFeats:
                self.over.emit(False, self.attemptId, errMsg)
                return
        else:
            selectedFeats, errMsg = self.checkSelectedFeats(self.selectedFeats[0], listSampFreq[0], listElectrodeList[0])
            if not selectedFeats:
                self.over.emit(False, self.attemptId, errMsg)
                return
            selectedFeats2, errMsg = self.checkSelectedFeats(self.selectedFeats[1], listSampFreq[0], listElectrodeList[0])
            if not selectedFeats2:
                self.over.emit(False, self.attemptId, errMsg)
                return

        # if freqRes != 1, modify the frequency indices of all features
        if self.freqRes != 1.0:
            if selectedFeats:
                for feat in selectedFeats:
                    feat[1] = str( int(float(feat[1]) /self.freqRes))

            if selectedFeats2:
                for feat in selectedFeats2:
                    feat[1] = str( int(float(feat[1]) /self.freqRes))

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
        self.extractDict["ChannelNames"] = ";".join(listElectrodeList[0])
        self.extractDict["AutoRegressiveOrder"] = str(
            timeToSamples(float(self.extractDict["AutoRegressiveOrderTime"]), listSampFreq[0]))
        self.extractDict["PsdSize"] = str(freqResToPsdSize(float(self.extractDict["FreqRes"]), listSampFreq[0]))

        # Special case : "connectivity shift", used in scenarios but not set that way
        # in the interface
        if "ConnectivityOverlap" in self.extractDict.keys():
            self.extractDict["ConnectivityShift"] = str(float(self.extractDict["ConnectivityLength"]) * (100.0 - float(self.extractDict["ConnectivityOverlap"])) / 100.0)

        # Case of a single feature type (power spectrum OR connectivity...)
        # RE-COPY sc2 & sc3 FROM TEMPLATE, SO THE USER CAN DO THIS MULTIPLE TIMES
        for i in [2, 3, 4, 5]:
            scenName = templateScenFilenames[i]
            print("---Copying file from folder " + str(__name__.split('.')[0] + '.' + self.templateFolder))
            with resources.path(str(__name__.split('.')[0] + '.' + self.templateFolder), scenName) as srcFile:
                destFile = os.path.join(self.workspaceFolder, scenName)
                print("---Copying file " + str(srcFile) + " to " + str(destFile))
                copyfile(srcFile, destFile)
            trainingpath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train")
            modifyScenarioGeneralSettings(str(destFile), self.extractDict)
            if i == 2:
                # training scenarios
                if not self.usingDualFeatures:
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT", "Classifier trainer", selectedFeats, epochCount[0], destFile)
                    # Special case: "connectivity metric"
                    if "ConnectivityMetric" in self.extractDict.keys():
                        modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destFile)
                else:
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT POWSPECTRUM", "Classifier trainer", selectedFeats, epochCount[0], destFile)
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT CONNECT", "Classifier trainer", selectedFeats2, epochCount[1], destFile)
                    modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destFile)

            elif i == 4 and not self.usingDualFeatures and self.parameterDict["pipelineType"] == optionKeys[2]:
                # "speed up" training scenarios (ONLY CONNECTIVITY)
                modifyTrainScenUsingSplitAndCsvWriter("SPLIT", selectedFeats, epochCount[0], destFile, trainingpath)

            elif i == 3:
                #  "online" scenario
                modifyAcqScenario(destFile, self.parameterDict["AcquisitionParams"])
                if not self.usingDualFeatures:
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT", "Classifier processor", selectedFeats, epochCount[0], destFile)
                    # Special case: "connectivity metric"
                    if "ConnectivityMetric" in self.extractDict.keys():
                        modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destFile)
                else:
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT POWSPECTRUM", "Classifier processor", selectedFeats, epochCount[0], destFile)
                    modifyTrainScenUsingSplitAndClassifiers("SPLIT CONNECT", "Classifier processor", selectedFeats2, epochCount[1], destFile)
                    modifyConnectivityMetric(self.extractDict["ConnectivityMetric"], destFile)



        # ------------------------------------------
        # TEST USING NEW SPLITTED "SPED UP" TRAINING
        # In this experimental setup, we want to avoid re-computing connectivity matrices
        # each time a training is attempted.
        # To this end, we use the connectivity matrices (as node strengths) computed in
        # the extraction step. For each run selected for the training, we compute a "temporary"
        # feature vector, and store it before we would feed it to the "classifier trainer" box in
        # openvibe.
        # When all runs have been processed that way, we aggregate all feature vectors (per class, per
        # feat), and feed those composite files to the feature aggregators and classifier trainer (in
        # scenario sc2-train-speedup-finalize.xml)
        if self.speedUp and self.parameterDict["pipelineType"] == optionKeys[2]:

            # "First step"
            scenFile = os.path.join(self.workspaceFolder, templateScenFilenames[4])
            analysisPath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "extract")
            trainingPath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train")

            self.info2.emit("Running first step (feature vector computation per run)")
            for run in trainingSigList:
                # MODIFY "FIRST STEP" SCENARIO
                runBasename = run.split("\\")[-1].removesuffix("-TRIALS.csv")
                modifyTrainingFirstStep(runBasename, len(selectedFeats), analysisPath, trainingPath, self.currentSessionId, scenFile)

                # RUN THE SCENARIO, with "False" to ignore training results
                success = self.runOvScenarioGeneric(os.path.join(self.workspaceFolder, scenFile))
                if not success:
                    successGlobal = False
                    self.errorMessageTrainer()
                    self.over.emit(False, self.attemptId, self.exitText)
                    break

            # NOW AGGREGATE FEATURE VECTORS PER FEATURE AND PER CLASS...
            self.info.emit(True)
            self.info2.emit("Combining Feature Vectors...")
            compositeFiles = []
            for classIdx in [1, 2]:
                for feat in range(len(selectedFeats)):
                    featFilesToMerge = []
                    for run in trainingSigList:
                        runBasename = run.split("\\")[-1].removesuffix("-TRIALS.csv")
                        runFeatClassCmb = str(runBasename + "-class" + str(classIdx) + "-feat" + str(feat+1) + ".csv" )
                        if os.path.exists(os.path.join(trainingPath, self.currentSessionId, runFeatClassCmb)):
                            featFilesToMerge.append(os.path.join(trainingPath, self.currentSessionId, runFeatClassCmb))

                    outCsv = mergeRunsCsv_new(featFilesToMerge)
                    compositeFiles.append(outCsv)

            # MODIFY "SECOND STEP" SCENARIO INPUTS & OUTPUT...
            scenFile = os.path.join(self.workspaceFolder, templateScenFilenames[5])
            newWeightsName = str("classifier-weights-" + self.attemptId + ".xml")
            modifyTrainingSecondStep(compositeFiles, len(selectedFeats), newWeightsName, self.currentSessionId, scenFile)
            modifyTrainPartitions(self.trainingSize, scenFile)

            self.info2.emit("Finalizing Training...")
            scenXml = os.path.join(self.workspaceFolder, templateScenFilenames[5])
            oneClass = False  # TODO: watch out and change that in the future, when speed-up is available.
            success, classifierOutputStr, accuracy = self.playClassifierScenario(scenXml, oneClass)
            if not success:
                successGlobal = False
                self.errorMessageTrainer()
                self.over.emit(False, self.attemptId, self.exitText)
            else:
                # Copy weights file to <workspaceFolder>/classifier-weights.xml
                newWeights = os.path.join(self.signalFolder, "sessions", self.currentSessionId, \
                                          "train", str("classifier-weights-" + self.attemptId + ".xml"))
                origFilename = os.path.join(self.workspaceFolder, "classifier-weights.xml")
                copyfile(newWeights, origFilename)

                self.currentAttempt["Score"] = accuracy

                # PREPARE GOODBYE MESSAGE...
                textFeats = str("")
                for i in range(len(trainingSigList)):
                    textFeats += str(os.path.basename(trainingSigList[i]) + "\n")

                textFeats += str("\nFeature(s) ")
                textFeats += str("(" + self.parameterDict["pipelineType"] + "):\n")
                for i in range(len(selectedFeats)):
                    actualFreq = selectedFeats[i][1]
                    if self.freqRes != 1.0:
                        actualFreq = str( float(selectedFeats[i][1]) * self.freqRes )
                    textFeats += str(
                        "\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(actualFreq) + " Hz\n")

                textDisplay = textFeats
                textDisplay += str("\n" + classifierOutputStr)

                self.exitText = textDisplay

        else:
            # ORIGINAL VERSION - NOT SPED UP
            # USING "CLASSIC" COMPOSITE FILE BUILDING + RUNNING TRAIN SCEN ON IT
            scenFile = os.path.join(self.workspaceFolder, templateScenFilenames[2])
            modifyTrainPartitions(self.trainingSize, scenFile)

            # Run the first training scenario  composite file from selected items
            class1Stim = "OVTK_GDF_Left"
            class2Stim = "OVTK_GDF_Right"
            tmin = 0
            tmax = float(self.extractDict["StimulationEpoch"])

            # Train on accumulation of all selected trials
            compositeCsv = mergeRunsCsv(trainingSigList, self.parameterDict["AcquisitionParams"]["Class1"],
                                        self.parameterDict["AcquisitionParams"]["Class2"],
                                        class1Stim, class2Stim, tmin, tmax)
            if not compositeCsv:
                self.over.emit(False, self.attemptId, "Error merging runs!! Most probably different list of electrodes")
                return

            print("Composite file for training: " + compositeCsv)
            compositeCsvBasename = os.path.basename(compositeCsv)
            newWeightsName = str("classifier-weights-" + self.attemptId + ".xml")
            modifyTrainIO(compositeCsvBasename, newWeightsName, self.currentSessionId, scenFile)

            # write composite file name in structure for future saving in workspace
            self.currentAttempt["CompositeFile"] = compositeCsvBasename

            # increment progressbar
            self.info.emit(True)
            self.info2.emit("Running Training Scenario")

            # RUN THE CLASSIFIER TRAINING SCENARIO
            scenXml = os.path.join(self.workspaceFolder, templateScenFilenames[2])
            oneClass = (self.parameterDict["pipelineType"] == optionKeys[4])
            success, classifierOutputStr, accuracy = self.playClassifierScenario(scenXml, oneClass)

            if not success:
                self.errorMessageTrainer()
                self.over.emit(False, self.attemptId, self.exitText)
            else:
                # Copy weights file to <workspaceFolder>/classifier-weights.xml
                newWeights = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", \
                                          str("classifier-weights-" + self.attemptId + ".xml"))
                origFilename = os.path.join(self.workspaceFolder, "classifier-weights.xml")
                copyfile(newWeights, origFilename)

                # write score in workspace structure for future reporting
                self.currentAttempt["Score"] = accuracy

                # PREPARE GOODBYE MESSAGE...
                textFeats = str("")
                for i in range(len(trainingSigList)):
                    textFeats += str(os.path.basename(trainingSigList[i]) + "\n")

                if not self.usingDualFeatures:
                    textFeats += str("\nFeature(s) ")
                    textFeats += str("(" + self.parameterDict["pipelineType"]+"):\n")
                    for i in range(len(selectedFeats)):
                        actualFreq = selectedFeats[i][1]
                        if self.freqRes != 1.0:
                            actualFreq = str( float(selectedFeats[i][1]) * self.freqRes )
                        textFeats += str("\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(actualFreq) + " Hz\n")


                else:
                    textFeats += str("\nFeature(s) for PowSpectrum:\n")
                    for i in range(len(selectedFeats)):
                        actualFreq = selectedFeats[i][1]
                        if self.freqRes != 1.0:
                            actualFreq = str( float(selectedFeats[i][1]) * self.freqRes )
                        textFeats += str("\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(actualFreq) + " Hz\n")

                    textFeats += str("Feature(s) for Connectivity:\n")
                    for i in range(len(selectedFeats2)):
                        actualFreq = selectedFeats2[i][1]
                        if self.freqRes != 1.0:
                            actualFreq = str( float(selectedFeats2[i][1]) * self.freqRes )
                        textFeats += str("\t" + "Channel " + str(selectedFeats2[i][0]) + " at " + str(actualFreq) + " Hz\n")

                textDisplay = textFeats
                textDisplay += str("\n" + classifierOutputStr)

                self.exitText = textDisplay


        self.stop = True
        self.over.emit(True, self.attemptId, self.exitText)

    def stopThread(self):
        self.stop = True

    def errorMessageTrainer(self):
        textError = str("Error running \"Training\" scenario\n")
        textError += str("Please try again with a lower number of partitions for k-fold test\n")
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

    def playClassifierScenario(self, scenFile, oneClass):
        # ----------
        # Run the provided training scenario, and check the console output for termination, errors, and
        # classification results
        # ----------

        # TODO WARNING : MAYBE CHANGE THAT IN THE FUTURE...
        # enableConfChange = False
        # if enableConfChange:
        #     # CHECK IF openvibe.conf has randomization of k-fold enabled
        #     # if not, change it
        #     confFile = os.path.join(os.path.dirname(self.ovScript), "share", "openvibe", "kernel", "openvibe.conf")
        #     if platform.system() == 'Windows':
        #         confFile = confFile.replace("/", "\\")
        #     modifyConf = False
        #     with open(confFile, 'r') as conf:
        #         confdata = conf.read()
        #         if "Plugin_Classification_RandomizeKFoldTestData = false" in confdata:
        #             modifyConf = True
        #             confdata = confdata.replace("Plugin_Classification_RandomizeKFoldTestData = false", "Plugin_Classification_RandomizeKFoldTestData = true")
        #     if modifyConf:
        #         with open(confFile, 'w') as conf:
        #             conf.write(confdata)

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
        activateScoreMsgBox = False
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
                    classifierOutputStr = str(classifierOutputStr + "\n")
                    break
                if "Cross-validation test" in str(output):
                    activateScoreMsgBox = True
                if activateScoreMsgBox:
                    stringToWrite = str(output).replace("\\r\\n\'", "")
                    if "trainer>" in stringToWrite:
                        stringToWrite = stringToWrite.split("trainer> ")
                        classifierOutputStr = str(classifierOutputStr + stringToWrite[1] + "\n")

        if activateScoreMsgBox:
            lines = classifierOutputStr.splitlines()

            target_1_True_Negative = float(lines[2].split()[2])
            target_1_False_Positive = float(lines[2].split()[3])
            target_2_False_Negative = float(lines[3].split()[2])
            target_2_True_Positive = float(lines[3].split()[3])

            precision_Class_1 = round(target_1_True_Negative / (target_1_True_Negative + target_2_False_Negative), 2)
            sensitivity_Class_1 = round(target_1_True_Negative / (target_1_True_Negative + target_1_False_Positive), 2)
            precision_Class_2 = round(target_2_True_Positive / (target_2_True_Positive + target_1_False_Positive), 2)
            sensitivity_Class_2 = round(target_2_True_Positive / (target_2_True_Positive + target_2_False_Negative), 2)

            accuracy = round(100.0 * (target_1_True_Negative + target_2_True_Positive) / (
                    target_1_True_Negative + target_1_False_Positive + target_2_False_Negative + target_2_True_Positive),
                             2)

            if (precision_Class_1 + sensitivity_Class_1) != 0:
                F_1_Score_Class_1 = round(
                    2 * precision_Class_1 * sensitivity_Class_1 / (precision_Class_1 + sensitivity_Class_1), 2)
            else:
                F_1_Score_Class_1 = 1.0
            if (precision_Class_2 + sensitivity_Class_2) != 0:
                F_1_Score_Class_2 = round(
                    2 * precision_Class_2 * sensitivity_Class_2 / (precision_Class_2 + sensitivity_Class_2), 2)
            else:
                F_1_Score_Class_2 = 1.0

            if not oneClass:
                messageClassif = "Overall accuracy : " + str(accuracy) + "%\n"
                messageClassif += "Class 1 | Precision  : " + str(precision_Class_1) + " | " + "Sensitivity : " + str(
                    sensitivity_Class_1)
                messageClassif += " | F_1 Score : " + str(F_1_Score_Class_1) + "\n"
                messageClassif += "Class 2 | Precision  : " + str(precision_Class_2) + " | " + "Sensitivity : " + str(
                    sensitivity_Class_2)
                messageClassif += " | F_1 Score : " + str(F_1_Score_Class_2)

                return success, messageClassif, accuracy

            if oneClass:
                messageClassif = "Precision  : " + str(precision_Class_2) + " | " + "Sensitivity : " + str(
                    sensitivity_Class_2)

                return success, messageClassif, (precision_Class_2*100.0)

        else:
            return success

    def runOvScenarioGeneric(self, scenXml):
        # ----------
        # Run a specified OpenViBE scenario. Filename must be absolute.
        # The console output is read only to find "Application terminated" or specific errors
        # ----------

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # Run actual command (openvibe-designer.cmd --no-gui --play-fast <scen.xml>)
        p = subprocess.Popen([command, "--invisible", "--play-fast", scenXml],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # Read console output to detect end of process
        # and prompt user with classification score. Quite artisanal but works
        success = True
        outputStr = ""
        activateScoreMsgBox = False
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "Invalid indexes: stopIdx - trainIndex = 1" in str(output):
                    success = False
                    return success
                if "Application terminated" in str(output):
                    outputStr = str(outputStr + "\n")
                    break

        return success

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
