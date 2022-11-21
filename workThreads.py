import sys
import os
import time
import subprocess
import platform
from shutil import copyfile

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal

from mergeRunsCsv import mergeRunsCsv
from extractMetaData import extractMetadata, generateMetadata
from modifyOpenvibeScen import *
from Visualization_Data import *
from featureExtractUtils import *
from utils import *

import bcipipeline_settings as settings


# ------------------------------------------------------
# CLASSES FOR LONG-RUNNING OPERATIONS IN THREADS
# ------------------------------------------------------

class Extraction(QtCore.QThread):
    info = pyqtSignal(bool)
    over = pyqtSignal(bool, str)

    def __init__(self, ovScript, scenFile, signalFiles, signalFolder,
                 parameterDict, parent=None):

        super().__init__(parent)
        self.stop = False
        self.ovScript = ovScript
        self.scenFile = scenFile
        self.signalFiles = signalFiles
        self.signalFolder = signalFolder
        self.parameterDict = parameterDict.copy()

    def run(self):
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        for signalFile in self.signalFiles:
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
            self.parameterDict["ChannelNames"] = ";".join(electrodeList)
            self.parameterDict["AutoRegressiveOrder"] = str(
                timeToSamples(float(self.parameterDict["AutoRegressiveOrderTime"]), sampFreq))
            self.parameterDict["PsdSize"] = str(freqResToPsdSize(float(self.parameterDict["FreqRes"]), sampFreq))

            # Special case : "subset of electrodes" for connectivity
            # DISABLED FOR NOW
            # if field is empty, use all electrodes
            # if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            #     if self.parameterDict["ChannelSubset"] == "":
            #         self.parameterDict["ChannelSubset"] = self.parameterDict["ChannelNames"]
            self.parameterDict["ChannelSubset"] = self.parameterDict["ChannelNames"]

            # Modify the scenario
            modifyScenarioGeneralSettings(self.scenFile, self.parameterDict)

            # Special case: "connectivity metric"
            if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
                if self.parameterDict["ConnectivityMetric"] == "MSC":
                    modifyConnectivityMetric("MagnitudeSquaredCoherence", self.scenFile)
                elif self.parameterDict["ConnectivityMetric"] == "IMCOH":
                    modifyConnectivityMetric("AbsImaginaryCoherence", self.scenFile)

            # Modify extraction scenario to use provided signal file, and rename outputs accordingly
            filename = signalFile.removesuffix(".ov")
            outputSpect1 = str(
                filename + "-" + self.parameterDict["pipelineType"] + "-" + self.parameterDict["Class1"] + ".csv")
            outputSpect2 = str(
                filename + "-" + self.parameterDict["pipelineType"] + "-" + self.parameterDict["Class2"] + ".csv")
            outputBaseline1 = str(filename + "-" + self.parameterDict["pipelineType"] + "-" + self.parameterDict[
                "Class1"] + "-BASELINE.csv")
            outputBaseline2 = str(filename + "-" + self.parameterDict["pipelineType"] + "-" + self.parameterDict[
                "Class2"] + "-BASELINE.csv")
            outputTrials = str(filename + "-TRIALS.csv")
            modifyExtractionIO(self.scenFile, signalFile, outputSpect1, outputSpect2,
                               outputBaseline1, outputBaseline2, outputTrials)

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

            self.info.emit(True)

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True


class LoadFilesForVizPowSpectrum(QtCore.QThread):
    info = pyqtSignal(bool)
    info2 = pyqtSignal(str)
    over = pyqtSignal(bool, str)

    def __init__(self, analysisFiles, signalFolder, parameterDict, Features, sampFreq, parent=None):

        super().__init__(parent)
        self.stop = False
        self.analysisFiles = analysisFiles
        self.signalFolder = signalFolder
        self.parameterDict = parameterDict.copy()
        self.Features = Features
        self.samplingFreq = sampFreq

        self.dataNp1 = []
        self.dataNp2 = []
        self.dataNp1baseline = []
        self.dataNp2baseline = []

    def run(self):

        listSampFreq = []
        listElectrodeList = []
        listFreqBins = []
        idxFile = 0

        suffix = "-" + self.parameterDict["pipelineType"]

        for selectedFilesForViz in self.analysisFiles:
            idxFile += 1
            pipelineLabel = self.parameterDict["pipelineType"]
            class1label = self.parameterDict["Class1"]
            class2label = self.parameterDict["Class2"]
            selectedBasename = selectedFilesForViz.removesuffix(suffix)

            path1 = os.path.join(self.signalFolder, "analysis",
                                 str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self.signalFolder, "analysis",
                                 str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))
            path1baseline = os.path.join(self.signalFolder, "analysis",
                                         str(selectedBasename + "-" + pipelineLabel + "-" + class1label + "-BASELINE.csv"))
            path2baseline = os.path.join(self.signalFolder, "analysis",
                                         str(selectedBasename + "-" + pipelineLabel + "-" + class2label + "-BASELINE.csv"))

            self.info2.emit(str("Loading Data for file " + str(idxFile)))
            [header1, data1] = load_csv_np(path1)
            [header2, data2] = load_csv_np(path2)
            self.info2.emit(str("Loading Baselines for file " + str(idxFile)))
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
                self.over.emit(False, errMsg)
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
                self.over.emit(False, errMsg)
                return

            listElectrodeList.append(electrodeList1)

            self.dataNp1.append(data1)
            self.dataNp2.append(data2)
            self.dataNp1baseline.append(data1baseline)
            self.dataNp2baseline.append(data2baseline)
            self.info.emit(True)

        # Check if all files have the same sampling freq and electrode list. If not, for now, we don't process further
        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg)
            return
        else:
            self.samplingFreq = listSampFreq[0]
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Electrode List mismatch")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        if not all(freqBins == listFreqBins[0] for freqBins in listFreqBins):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Not same number of frequency bins (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg)
            return
        else:
            print("Frequency bins: " + str(listFreqBins[0]))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.parameterDict["StimulationEpoch"])
        trials = int(self.parameterDict["TrialNb"])
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqBins[0]
        winLen = float(self.parameterDict["TimeWindowLength"])
        winShift = float(self.parameterDict["TimeWindowShift"])

        # electrodes_orig = channel_generator(nbElectrodes, 'TP9', 'TP10')
        # Replace "ground" and "ref" electrodes (eg TP9/TP10) with new grounds and ref (eg AFz and FCz)
        ground = 'TP9'
        newGround = 'FPz'
        ref = 'TP10'
        newRef = 'FCz'
        electrodes_orig = elecGroundRef(electrodeList, ground, newGround, ref, newRef)
        if not electrodes_orig:
            errMsg = str("Problem with the list of electrodes...")
            self.over.emit(False, errMsg)
            return

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
            power_cond1_baseline, timefreq_cond1_baseline = \
                Extract_CSV_Data(self.dataNp1baseline[run], trialLength, nbElectrodes, n_bins, winLen, winShift)
            power_cond2_baseline, timefreq_cond2_baseline = \
                Extract_CSV_Data(self.dataNp2baseline[run], trialLength, nbElectrodes, n_bins, winLen, winShift)

            if power_cond1_final is None:
                power_cond1_final = power_cond1
                power_cond2_final = power_cond2
                power_cond1_baseline_final = power_cond1_baseline
                power_cond2_baseline_final = power_cond2_baseline
                timefreq_cond1_final = timefreq_cond1
                timefreq_cond2_final = timefreq_cond2
                timefreq_cond1_baseline_final = timefreq_cond1_baseline
                timefreq_cond2_baseline_final = timefreq_cond2_baseline
            else:
                power_cond1_final = np.concatenate((power_cond1_final, power_cond1))
                power_cond2_final = np.concatenate((power_cond2_final, power_cond2))
                power_cond1_baseline_final = np.concatenate((power_cond1_baseline_final, power_cond1_baseline))
                power_cond2_baseline_final = np.concatenate((power_cond2_baseline_final, power_cond2_baseline))
                timefreq_cond1_final = np.concatenate((timefreq_cond1_final, timefreq_cond1))
                timefreq_cond2_final = np.concatenate((timefreq_cond2_final, timefreq_cond2))
                timefreq_cond1_baseline_final = np.concatenate((timefreq_cond1_baseline_final, timefreq_cond1_baseline),
                                                               axis=2)
                timefreq_cond2_baseline_final = np.concatenate((timefreq_cond2_baseline_final, timefreq_cond2_baseline),
                                                               axis=2)

        self.info2.emit("Computing statistics")

        trialLengthSec = float(self.parameterDict["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        windowLength = float(self.parameterDict["TimeWindowLength"])
        windowShift = float(self.parameterDict["TimeWindowShift"])
        segmentsPerTrial = round((trialLength - windowLength) / windowShift)
        fres = float(self.parameterDict["FreqRes"])

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
        Wsquare, Wpvalues = Compute_Wilcoxon_Map(power_cond2_final[:, :, :(n_bins - 1)],
                                                 power_cond1_final[:, :, :(n_bins - 1)])

        Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
            = Reorder_plusplus(Rsigned, Wsquare, Wpvalues, electrodes_orig, power_cond1_final, power_cond2_final,
                               timefreq_cond1_final, timefreq_cond2_final)

        self.Features.electrodes_orig = electrodes_orig
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
        self.Features.Wsigned = Wsquare_2

        self.Features.average_baseline_cond1 = np.mean(power_cond1_baseline_final, axis=0)
        self.Features.std_baseline_cond1 = np.std(power_cond1_baseline_final, axis=0)
        self.Features.average_baseline_cond2 = np.mean(power_cond2_baseline_final, axis=0)
        self.Features.std_baseline_cond2 = np.std(power_cond2_baseline_final, axis=0)

        self.Features.samplingFreq = self.samplingFreq

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True

# Class for loading extracted data in the "Connectivity Pipeline"
# data are NODE STRENGTH (not raw connectivity matrices), we manage them
# almost like power spectra...
class LoadFilesForVizConnectivity(QtCore.QThread):
    info = pyqtSignal(bool)
    info2 = pyqtSignal(str)
    over = pyqtSignal(bool, str)

    def __init__(self, analysisFiles, signalFolder, parameterDict, Features, sampFreq, parent=None):

        super().__init__(parent)
        self.stop = False
        self.analysisFiles = analysisFiles
        self.signalFolder = signalFolder
        self.parameterDict = parameterDict.copy()
        self.Features = Features
        self.samplingFreq = sampFreq

        self.dataNp1 = []
        self.dataNp2 = []

    def run(self):

        listSamplingFreqs = []
        listFreqs = []
        listElectrodeList = []
        idxFile = 0

        suffix = "-" + self.parameterDict["pipelineType"]

        for selectedFilesForViz in self.analysisFiles:
            idxFile += 1
            pipelineLabel = self.parameterDict["pipelineType"]
            class1label = self.parameterDict["Class1"]
            class2label = self.parameterDict["Class2"]
            selectedBasename = selectedFilesForViz.removesuffix(suffix)

            # First, get metadata...
            metapath = os.path.join(self.signalFolder, str(selectedBasename + "-META.csv"))
            [sampFreq, electrodeList] = extractMetadata(metapath)
            listSamplingFreqs.append(sampFreq)

            # Now load data...
            path1 = os.path.join(self.signalFolder, "analysis",
                                 str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self.signalFolder, "analysis",
                                 str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))

            self.info2.emit(str("Loading Data for file " + str(idxFile)))
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
                self.over.emit(False, errMsg)
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
                self.over.emit(False, errMsg)
                return

            listElectrodeList.append(electrodeList1)

            self.dataNp1.append(data1)
            self.dataNp2.append(data2)

            self.info.emit(True)

        # Check if all files have the same sampling freq and electrode list. If not, for now, we don't process further
        if not all(nbfreqs == listFreqs[0] for nbfreqs in listFreqs):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "nb of frequency mismatch (" + str(listFreqs) + ")")
            self.over.emit(False, errMsg)
            return
        else:
            print("Nb of Frequency bins for selected files : " + str(listFreqs[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sensor List mismatch")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        if not all(sampFreq == listSamplingFreqs[0] for sampFreq in listSamplingFreqs):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling Freq mismatch")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.parameterDict["StimulationEpoch"])
        trials = int(self.parameterDict["TrialNb"])
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqs[0]
        connectLength = float(self.parameterDict["ConnectivityLength"])
        connectOverlap = float(self.parameterDict["ConnectivityOverlap"])
        sampFreq = listSamplingFreqs[0]

        # TODO : later (pb with subset...)
        # Replace "ground" and "ref" electrodes (eg TP9/TP10) with new grounds and ref (eg AFz and FCz)
        ground = 'TP9'
        newGround = 'FPz'
        ref = 'TP10'
        newRef = 'FCz'
        electrodes_orig = elecGroundRef(electrodeList, ground, newGround, ref, newRef)
        if not electrodes_orig:
            errMsg = str("Problem with the list of electrodes...")
            self.over.emit(False, errMsg)
            return

        # For multiple runs (ie. multiple selected CSV files), we just concatenate
        # the trials from all files. Then the displayed spectral features (R²map, PSD, topography)
        # will be computed as averages over all the trials.
        connect_cond1_final = None
        connect_cond2_final = None
        idxFile = 0
        for run in range(len(self.dataNp1)):
            idxFile += 1
            self.info2.emit(str("Processing data for file " + str(idxFile)))
            connect_cond1 = Extract_Connect_NodeStrength_CSV_Data(self.dataNp1[run], trialLength, nbElectrodes, n_bins,
                                                                  connectLength, connectOverlap)
            connect_cond2 = Extract_Connect_NodeStrength_CSV_Data(self.dataNp2[run], trialLength, nbElectrodes, n_bins,
                                                                  connectLength, connectOverlap)
            if connect_cond1_final is None:
                connect_cond1_final = connect_cond1
                connect_cond2_final = connect_cond2
            else:
                connect_cond1_final = np.concatenate((connect_cond1_final, connect_cond1))
                connect_cond2_final = np.concatenate((connect_cond2_final, connect_cond2))

        self.info2.emit("Computing statistics")

        trialLengthSec = float(self.parameterDict["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        fres = float(self.parameterDict["FreqRes"])

        # Statistical Analysis...
        freqs_array = np.arange(0, n_bins, fres)
        Rsigned = Compute_Rsquare_Map(connect_cond2_final[:, :, :(n_bins - 1)],
                                      connect_cond1_final[:, :, :(n_bins - 1)])

        Rsigned_2, electrodes_final, connect_cond1_2, connect_cond2_2, \
            = Reorder_Rsquare(Rsigned, electrodes_orig, connect_cond1_final, connect_cond2_final)

        # Fill Features struct...
        self.Features.electrodes_orig = electrodes_orig
        # self.Features.electrodes_orig = electrodeList
        self.Features.electrodes_final = electrodes_final
        # self.Features.connect_cond1 = connect_cond1_2
        # self.Features.connect_cond2 = connect_cond2_2
        self.Features.power_cond1 = connect_cond1_2
        self.Features.power_cond2 = connect_cond2_2
        self.Features.fres = fres
        self.Features.samplingFreq = sampFreq
        self.Features.freqs_array = freqs_array

        self.Features.Rsigned = Rsigned_2

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True


class TrainClassifier(QtCore.QThread):
    info = pyqtSignal(bool)
    info2 = pyqtSignal(str)
    over = pyqtSignal(bool, str)

    def __init__(self, isCombinationComputing, trainingFiles,
                 signalFolder, templateFolder, scriptFolder, ovScript,
                 trainingSize, selectedFeats,
                 parameterDict, sampFreq, parent=None):

        super().__init__(parent)
        self.stop = False
        self.isCombinationComputing = isCombinationComputing
        self.trainingFiles = trainingFiles
        self.signalFolder = signalFolder
        self.templateFolder = templateFolder
        self.scriptFolder = scriptFolder
        self.ovScript = ovScript
        self.trainingSize = trainingSize
        self.selectedFeats = selectedFeats
        self.parameterDict = parameterDict.copy()
        self.samplingFreq = sampFreq
        self.exitText = ""

    def run(self):
        # Get electrodes lists and sampling freqs, and check that they match
        # + that the selected channels are in the list of electrodes
        compositeSigList = []
        listSampFreq = []
        listElectrodeList = []
        for trainingFile in self.trainingFiles:
            path = os.path.join(self.signalFolder, "training", trainingFile)
            header = pd.read_csv(path, nrows=0).columns.tolist()
            listSampFreq.append(int(header[0].split(':')[1].removesuffix('Hz')))
            listElectrodeList.append(header[2:-3])
            compositeSigList.append(path)

        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sampling Frequency for selected files : " + str(listSampFreq[0]))

        if not all(electrodeList == listElectrodeList[0] for electrodeList in listElectrodeList):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Electrode List mismatch")
            self.over.emit(False, errMsg)
            return
        else:
            print("Sensor list for selected files : " + ";".join(listElectrodeList[0]))

        selectedFeats, errMsg = self.checkSelectedFeats(listSampFreq[0], listElectrodeList[0])
        if not selectedFeats:
            self.over.emit(False, errMsg)
            return

        epochCount = 0
        epochAvg = False
        if self.parameterDict["pipelineType"] == "PowSpectrumGraz":
            stimEpochLength = self.parameterDict["StimulationEpoch"]
            winShift = self.parameterDict["TimeWindowShift"]
            epochCount = np.floor(float(stimEpochLength) / float(winShift))
            epochAvg = True

        # RE-COPY sc2 & sc3 FROM TEMPLATE, SO THE USER CAN DO THIS MULTIPLE TIMES...
        for i in [2, 3]:
            scenName = settings.templateScenFilenames[i]
            srcFile = os.path.join(self.templateFolder, scenName)
            destFile = os.path.join(self.scriptFolder, "generated", scenName)
            print("---Copying file " + srcFile + " to " + destFile)
            copyfile(srcFile, destFile)
            modifyScenarioGeneralSettings(destFile, self.parameterDict)
            if i == 2:
                modifyTrainScenario(selectedFeats, epochAvg, epochCount, destFile)
                # Special case: "connectivity metric"
                if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
                    if self.parameterDict["ConnectivityMetric"] == "MSC":
                        modifyConnectivityMetric("MagnitudeSquaredCoherence", destFile)
                    elif self.parameterDict["ConnectivityMetric"] == "IMCOH":
                        modifyConnectivityMetric("AbsImaginaryCoherence", destFile)
            elif i == 3:
                modifyAcqScenario(destFile, self.parameterDict, True)
                modifyOnlineScenario(selectedFeats, destFile)
                # Special case: "connectivity metric"
                if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
                    if self.parameterDict["ConnectivityMetric"] == "MSC":
                        modifyConnectivityMetric("MagnitudeSquaredCoherence", destFile)
                    elif self.parameterDict["ConnectivityMetric"] == "IMCOH":
                        modifyConnectivityMetric("AbsImaginaryCoherence", destFile)

        scenFile = os.path.join(self.scriptFolder, "generated", settings.templateScenFilenames[2])
        modifyTrainPartitions(self.trainingSize, scenFile)

        # Create composite file from selected items
        class1Stim = "OVTK_GDF_Left"
        class2Stim = "OVTK_GDF_Right"
        tmin = 0
        tmax = float(self.parameterDict["StimulationEpoch"])

        if not self.isCombinationComputing:
            compositeCsv = mergeRunsCsv(compositeSigList, self.parameterDict["Class1"], self.parameterDict["Class2"],
                                        class1Stim, class2Stim, tmin, tmax)
            if not compositeCsv:
                self.over.emit(False, "Error merging runs!! Most probably different list of electrodes")
                return

            self.info.emit(True)

            print("Composite file for training: " + compositeCsv)
            compositeCsvBasename = os.path.basename(compositeCsv)
            newWeightsName = "classifier-weights.xml"
            modifyTrainIO(compositeCsvBasename, newWeightsName, scenFile)

            self.info2.emit("Running Training Scenario")

            # RUN THE CLASSIFIER TRAINING SCENARIO
            success, classifierScoreStr, accuracy = self.runClassifierScenario()

            if not success:
                self.errorMessageTrainer()
            else:
                # Copy weights file to generated/classifier-weights.xml
                newWeights = os.path.join(self.signalFolder, "training", "classifier-weights.xml")
                origFilename = os.path.join(self.scriptFolder, "generated", "classifier-weights.xml")
                copyfile(newWeights, origFilename)

                # PREPARE GOODBYE MESSAGE...
                textFeats = str("Using spectral features:\n")
                for i in range(len(selectedFeats)):
                    textFeats += str("  Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")

                textGoodbye = str("Results written in file:\t generated/classifier-weights.xml\n")
                textGoodbye += str(
                    "If those results are satisfying, you can now open generated/sc3-online.xml in the Designer")

                textDisplay = textFeats
                textDisplay += str("\n\n" + classifierScoreStr)
                textDisplay += str("\n\n" + textGoodbye)

                self.exitText = textDisplay

        else:
            # Create list of files from selected items
            combinationsList = list(myPowerset(compositeSigList))
            sigIdxList = range(len(compositeSigList))
            combIdx = list(myPowerset(sigIdxList))
            scores = [0 for x in range(len(combIdx))]
            classifierScoreStrList = ["" for x in range(len(combIdx))]

            successGlobal = True
            for idxcomb, comb in enumerate(combinationsList):
                newLabel = str("Combination " + str(combIdx[idxcomb]))
                self.info2.emit(newLabel)

                sigList = []
                for file in comb:
                    sigList.append(file)
                compositeCsv = mergeRunsCsv(sigList, self.parameterDict["Class1"], self.parameterDict["Class2"],
                                            class1Stim, class2Stim, tmin, tmax)
                if not compositeCsv:
                    self.over.emit(False, "Error merging runs!! Most probably different list of electrodes")
                    return

                print("Composite file for training: " + compositeCsv)
                compositeCsvBasename = os.path.basename(compositeCsv)
                newWeightsName = str("classifier-weights-" + str(idxcomb) + ".xml")
                modifyTrainIO(compositeCsvBasename, newWeightsName, scenFile)

                # RUN THE CLASSIFIER TRAINING SCENARIO
                success, classifierScoreStrList[idxcomb], scores[idxcomb] = self.runClassifierScenario()
                if not success:
                    successGlobal = False
                    self.errorMessageTrainer()
                    break

                self.info.emit(True)

            if not successGlobal:
                self.errorMessageTrainer()
            else:
                # Find max score
                maxIdx = scores.index(max(scores))
                # Copy weights file to generated/classifier-weights.xml
                maxFilename = os.path.join(self.scriptFolder, "generated", "signals", "training", "classifier-weights-")
                maxFilename += str(str(maxIdx) + ".xml")
                origFilename = os.path.join(self.scriptFolder, "generated", "classifier-weights.xml")
                copyfile(maxFilename, origFilename)

                # ==========================
                # PREPARE GOODBYE MESSAGE...
                textFeats = str("Using spectral features:\n")
                for i in range(len(selectedFeats)):
                    textFeats += str("\tChannel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
                textFeats += str("\n... and experiment runs:")
                for i in range(len(compositeSigList)):
                    textFeats += str("\n\t[" + str(i) + "]: " + os.path.basename(compositeSigList[i]))

                textScore = str("Training Cross-Validation Test Accuracies per combination:\n")
                for i in range(len(combIdx)):
                    combIdxStr = []
                    for j in combIdx[i]:
                        combIdxStr.append(str(j))
                    textScore += str("\t[" + ",".join(combIdxStr) + "]: " + str(scores[i]) + "%\n")
                maxIdxStr = []
                for j in combIdx[maxIdx]:
                    maxIdxStr.append(str(j))
                textScore += str("\nMax is combination [" + ','.join(maxIdxStr) + "] with " + str(max(scores)) + "%\n")
                textScore += classifierScoreStrList[maxIdx]

                textGoodbye = str("The weights for this combination have been written to:\n")
                textGoodbye += str("\tgenerated/classifier-weights.xml\n")
                textGoodbye += str("If those results are satisfying, you can now open this scenario in the Designer:\n")
                textGoodbye += str("\tgenerated/sc3-online.xml")

                textDisplay = textFeats
                textDisplay = str(textDisplay + "\n\n" + textScore)
                textDisplay = str(textDisplay + "\n\n" + textGoodbye)

                self.exitText = textDisplay

        self.stop = True
        self.over.emit(True, self.exitText)

    def stopThread(self):
        self.stop = True

    def errorMessageTrainer(self):
        textError = str("Error running \"Training\" scenario\n")
        textError += str("Please try again with a lower number of partitions for k-fold test\n")
        self.exitText = textError

    def checkSelectedFeats(self, sampFreq, electrodeList):
        selectedFeats = []
        errMsg = ""
        # Checks :
        # - No empty field
        # - frequencies in acceptable ranges
        # - channels in list
        n_bins = int((sampFreq / 2) + 1)
        for idx, feat in enumerate(self.selectedFeats):
            if feat.text() == "":
                errMsg = str("Pair " + str(idx + 1) + " is empty...")
                return None, errMsg
            [chan, freqstr] = feat.text().split(";")
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
            selectedFeats.append(feat.text().split(";"))
            print(feat)

        return selectedFeats, errMsg

    def runClassifierScenario(self):
        # ----------
        # Run the classifier training scen (sc2-train.xml), using the provided parameters
        # and features
        # ----------
        scenFile = os.path.join(self.scriptFolder, "generated", settings.templateScenFilenames[2])

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
        classifierScoreStr = ""
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
                    classifierScoreStr = str(classifierScoreStr + "\n")
                    break
                if "Cross-validation test" in str(output):
                    activateScoreMsgBox = True
                if activateScoreMsgBox:
                    stringToWrite = str(output).replace("\\r\\n\'", "")
                    if "trainer>" in stringToWrite:
                        stringToWrite = stringToWrite.split("trainer> ")
                        classifierScoreStr = str(classifierScoreStr + stringToWrite[1] + "\n")

        lines = classifierScoreStr.splitlines()

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

        F_1_Score_Class_1 = round(
            2 * precision_Class_1 * sensitivity_Class_1 / (precision_Class_1 + sensitivity_Class_1), 2)
        F_1_Score_Class_2 = round(
            2 * precision_Class_2 * sensitivity_Class_2 / (precision_Class_2 + sensitivity_Class_2), 2)

        messageClassif = "Overall accuracy : " + str(accuracy) + "%\n"
        messageClassif += "Class 1 | Precision  : " + str(precision_Class_1) + " | " + "Sensitivity : " + str(
            sensitivity_Class_1)
        messageClassif += " | F_1 Score : " + str(F_1_Score_Class_1) + "\n"
        messageClassif += "Class 2 | Precision  : " + str(precision_Class_2) + " | " + "Sensitivity : " + str(
            sensitivity_Class_2)
        messageClassif += " | F_1 Score : " + str(F_1_Score_Class_2)

        return success, messageClassif, accuracy