import sys
import os
import time
import subprocess
import platform
from shutil import copyfile
from importlib import resources
import mne
from PySide2 import QtCore
from PySide2.QtCore import Signal

from lib.mergeRunsCsv import mergeRunsCsv, mergeRunsCsv_new
from lib.extractMetaData import extractMetadata, generateMetadata
from lib.fileLoading import *
from lib.modifyOpenvibeScen import *
from lib.Visualization_Data import *
from lib.featureExtractUtils import *
from lib.utils import *
from lib.Spectral_Analysis import *
from lib.bcipipeline_settings import *

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
            ## Load the signal
            car_bool = False # outside parameter for CAR for later ?
            cond1 = 'OVTK_GDF_Left'
            cond2 = 'OVTK_GDF_Right'
            tmin = float(pipelineExtractSettings["PowSpectrumGraz"]["StimulationDelay"])
            tmax = tmin + float(pipelineExtractSettings["PowSpectrumGraz"]["StimulationEpoch"])




            ## Load EEG files
            raw_EDF, events_from_annot, event_id = load_file(self.signalFolder, signalFile, car_bool)
            sampFreq = raw_EDF.info["sfreq"]
            electrodeList = raw_EDF.info["ch_names"]
            Epoch_compute_CLASS_1 = select_Event(cond1, raw_EDF, events_from_annot, event_id, tmin, tmax,len(electrodeList))
            Epoch_compute_CLASS_2 = select_Event(cond2, raw_EDF, events_from_annot, event_id, tmin, tmax,len(electrodeList))

            ## Meta Data information
            self.extractDict["ChannelNames"] = ";".join(electrodeList)
            self.extractDict["AutoRegressiveOrder"] = str(
                timeToSamples(float(self.extractDict["AutoRegressiveOrderTime"]), sampFreq))
            self.extractDict["PsdSize"] = str(freqResToPsdSize(float(self.extractDict["FreqRes"]), sampFreq))

            nper_segSamples = int(sampFreq*float(pipelineExtractSettings["PowSpectrumGraz"]["TimeWindowLength"]))
            shiftSamples = int(sampFreq*float(pipelineExtractSettings["PowSpectrumGraz"]["TimeWindowShift"]))
            noverlapSamples = nper_segSamples-shiftSamples
            nfft = int(sampFreq/float(pipelineExtractSettings["PowSpectrumGraz"]["FreqRes"]))

            filter_order = self.extractDict["AutoRegressiveOrder"]

            ## CAR for PSD computation
            Epoch_compute_CLASS_1_CAR,ref_data = mne.set_eeg_reference(Epoch_compute_CLASS_1, ref_channels='average')
            Epoch_compute_CLASS_2_CAR, ref_data = mne.set_eeg_reference(Epoch_compute_CLASS_2, ref_channels='average')



            Psd_CLASS_1, Timefreq_CLASS_1, Time_CLASS_1 = \
                Power_burg_calculation(Epoch_compute_CLASS_1_CAR.get_data()[:,:,:], noverlapSamples, nfft, sampFreq, nper_segSamples, False,filter_order)
            Psd_CLASS_2, Timefreq_CLASS_2, Time_CLASS_2 = \
                Power_burg_calculation(Epoch_compute_CLASS_2_CAR.get_data()[:,:,:], noverlapSamples, nfft, sampFreq, nper_segSamples,
                                       False, filter_order)

            self.info.emit(True)    # send "info" signal to increment progressbar
            tstop = time.perf_counter()
            print("= Extraction from file " + signalFile + " finished in " + str(tstop-tstart))

        self.stop = True
        self.over.emit(True, "")

    def stopThread(self):
        self.stop = True


class LoadFilesForVizPowSpectrum(QtCore.QThread):
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

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
        self.dataNp1baseline = []
        self.dataNp2baseline = []

    def run(self):

        listSampFreq = []
        listElectrodeList = []
        listFreqBins = []
        idxFile = 0

        for selectedFilesForViz in self.analysisFiles:
            idxFile += 1
            pipelineLabel = "SPECTRUM"
            class1label = self.parameterDict["AcquisitionParams"]["Class1"]
            class2label = self.parameterDict["AcquisitionParams"]["Class2"]
            selectedBasename = selectedFilesForViz

            path1 = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class1label + ".csv"))
            path2 = os.path.join(self. workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class2label + ".csv"))
            path1baseline = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class1label + "-BASELINE.csv"))
            path2baseline = os.path.join(self.workingFolder, str(selectedBasename + "-" + pipelineLabel + "-" + class2label + "-BASELINE.csv"))

            self.info2.emit(str("Loading " + pipelineLabel + " Data for file " + str(idxFile) + " : " + selectedFilesForViz))
            [header1, data1] = load_csv_np(path1)
            [header2, data2] = load_csv_np(path2)
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
                timefreq_cond1_baseline_final = np.concatenate((timefreq_cond1_baseline_final, timefreq_cond1_baseline))
                timefreq_cond2_baseline_final = np.concatenate((timefreq_cond2_baseline_final, timefreq_cond2_baseline))

        self.info2.emit("Computing statistics")

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
        Wsquare, Wpvalues = Compute_Wilcoxon_Map(power_cond2_final[:, :, :(n_bins - 1)],
                                                 power_cond1_final[:, :, :(n_bins - 1)])

        # Reordering for R map and topography...
        if self.parameterDict["sensorMontage"] == "standard_1020" \
            or self.parameterDict["sensorMontage"] == "biosemi64":
            Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_plusplus(Rsigned, Wsquare, Wpvalues, electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)
        elif self.parameterDict["sensorMontage"] == "custom" \
            and self.parameterDict["customMontagePath"] != "":
            Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
                = Reorder_custom_plus(Rsigned, Wsquare, Wpvalues, self.parameterDict["customMontagePath"], electrodeList, power_cond1_final, power_cond2_final,
                                   timefreq_cond1_final, timefreq_cond2_final)

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
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

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
        trialLength = float(self.extractDict["StimulationEpoch"])
        trials = int(self.parameterDict["AcquisitionParams"]["TrialNb"])
        electrodeList = listElectrodeList[0]
        nbElectrodes = len(electrodeList)
        n_bins = listFreqs[0]
        connectLength = float(self.extractDict["ConnectivityLength"])
        connectOverlap = float(self.extractDict["ConnectivityOverlap"])
        sampFreq = listSamplingFreqs[0]

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
        trialLengthSec = float(self.parameterDict["AcquisitionParams"]["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        fres = float(self.extractDict["FreqRes"])

        # Statistical Analysis...
        freqs_array = np.arange(0, n_bins, fres)
        Rsigned = Compute_Rsquare_Map(connect_cond2_final[:, :, :(n_bins - 1)],
                                      connect_cond1_final[:, :, :(n_bins - 1)])


        # Reordering for R map and topography...
        if self.parameterDict["sensorMontage"] == "standard_1020" \
            or self.parameterDict["sensorMontage"] == "biosemi64":
            Rsigned_2, electrodes_final, connect_cond1_2, connect_cond2_2, \
                = Reorder_Rsquare(Rsigned, electrodeList, connect_cond1_final, connect_cond2_final)

        elif self.parameterDict["sensorMontage"] == "custom" \
            and self.parameterDict["customMontagePath"] != "":
            Rsigned_2, electrodes_final, connect_cond1_2, connect_cond2_2, \
                = Reorder_custom(Rsigned, self.parameterDict["customMontagePath"], electrodeList, connect_cond1_final, connect_cond2_final,)

        # Fill Features struct...
        self.Features.electrodes_orig = electrodeList
        self.Features.electrodes_final = electrodes_final
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
    info = Signal(bool)
    info2 = Signal(str)
    over = Signal(bool, str)

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
        self.selectedFeats = selectedFeats
        self.parameterDict = parameterDict.copy()
        self.currentSessionId = self.parameterDict["currentSessionId"]
        self.extractDict = parameterDict["Sessions"][self.parameterDict["currentSessionId"]]["ExtractionParams"].copy()
        self.samplingFreq = sampFreq
        self.exitText = ""

        self.usingDualFeatures = self.parameterDict["pipelineType"] == optionKeys[3]

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

        selectedFeats = None
        selectedFeats2 = None
        if not self.usingDualFeatures:
            selectedFeats, errMsg = self.checkSelectedFeats(self.selectedFeats, listSampFreq[0], listElectrodeList[0])
            if not selectedFeats:
                self.over.emit(False, errMsg)
                return
        else:
            selectedFeats, errMsg = self.checkSelectedFeats(self.selectedFeats[0], listSampFreq[0], listElectrodeList[0])
            if not selectedFeats:
                self.over.emit(False, errMsg)
                return
            selectedFeats2, errMsg = self.checkSelectedFeats(self.selectedFeats[1], listSampFreq[0], listElectrodeList[0])
            if not selectedFeats2:
                self.over.emit(False, errMsg)
                return

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
        elif self.parameterDict["pipelineType"] == optionKeys[3]:
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
                modifyAcqScenario(destFile, self.parameterDict["AcquisitionParams"], True)
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
                    self.over.emit(False, self.exitText)
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
            success, classifierOutputStr, accuracy = self.runClassifierScenario(scenXml)
            if not success:
                successGlobal = False
                self.errorMessageTrainer()
                self.over.emit(False, self.exitText)
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
                    textFeats += str(
                        "\t" + "Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")

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
                self.over.emit(False, "Error merging runs!! Most probably different list of electrodes")
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
            success, classifierOutputStr, accuracy = self.runClassifierScenario(scenXml)

            if not success:
                self.errorMessageTrainer()
                self.over.emit(False, self.exitText)
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
                textDisplay += str("\n" + classifierOutputStr)

                self.exitText = textDisplay


        self.stop = True
        self.over.emit(True, self.exitText)

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

    def runClassifierScenario(self, scenFile):
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

