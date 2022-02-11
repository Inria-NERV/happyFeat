import sys
import os
import subprocess
import platform
import json
import pandas as pd
import time
import numpy as np
import matplotlib.pyplot as plt
from shutil import copyfile

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QSizePolicy

from PyQt5.QtCore import QTimer

from Visualization_Data import *
from featureExtractUtils import *
from modifyOpenvibeScen import *
from mergeRuns import mergeRuns

import bcipipeline_settings as settings

class Features:
    Rsigned = []
    Wsigned = []
    electrodes_orig = []
    electrodes_final = []

    power_cond1 = []
    power_cond2 = []
    timefreq_cond1 = []
    timefreq_cond2 = []

    freqs_array = []
    time_array = []

    average_baseline_cond1 = []
    std_baseline_cond1 = []
    average_baseline_cond2 = []
    std_baseline_cond2 = []


class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        # -----------------------------------------------------------------------
        # GET PARAMS FROM JSON FILE...
        self.dataNp1 = []
        self.dataNp2 = []
        self.Features = Features()

        # Sampling Freq: to be loaded later, in Spectrum CSV files
        self.samplingFreq = None

        self.scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        print(self.scriptPath)
        jsonfullpath = os.path.join(self.scriptPath, "generated", "params.json")
        with open(jsonfullpath) as jsonfile:
            self.parameterDict = json.load(jsonfile)

        self.ovScript = self.parameterDict["ovDesignerPath"]

        # TODO : get from interface/files !!
        self.fres = 1

        # -----------------------------------------------------------------------
        # CREATE INTERFACE...
        # dlgLayout : Entire Window, separated in horizontal pannels
        # Left-most: layoutExtract (for running sc2-extract)
        # Center: Visualization
        # Right-most: Feature Selection & classifier training
        self.setWindowTitle('goodViBEs / happyFeatS - Feature Selection interface')
        self.dlgLayout = QHBoxLayout()

        # -----------------------------------------------------------------------
        # LEFT PART : Extraction from signal files (sc2-extract.xml)
        self.layoutExtract = QVBoxLayout()

        # TODO : keep this part ? OPENVIBE DESIGNER FINDER
        self.btn_browseOvScript = QPushButton("Browse for OpenViBE designer script")
        self.btn_browseOvScript.clicked.connect(lambda: self.browseForDesigner())
        self.designerWidget = QWidget()
        layout_h = QHBoxLayout(self.designerWidget)
        self.designerTextBox = QLineEdit()
        self.designerTextBox.setText(str(self.ovScript))
        self.designerTextBox.setEnabled(False)
        layout_h.addWidget(self.designerTextBox)
        layout_h.addWidget(self.btn_browseOvScript)

        # FILE LOADING (from .ov file(s)) 
        # AND RUNNING SCENARIO FOR SPECTRA EXTRACTION
        labelSignal = str("===== FEATURE EXTRACTION FROM SIGNAL FILES =====")
        self.labelSignal = QLabel(labelSignal)
        self.labelSignal.setAlignment(QtCore.Qt.AlignCenter)

        self.fileListWidget = QListWidget()
        self.fileListWidget.setSelectionMode(QListWidget.MultiSelection)

        # Generate button
        self.btn_runExtractionScenario = QPushButton("Generate Spectrum Files")
        self.btn_runExtractionScenario.clicked.connect(lambda: self.runExtractionScenario())

        # Label + un-editable list of parameters for reminder
        labelReminder = str("--- Used parameters (set in Generator GUI) ---")
        self.labelReminder = QLabel(labelReminder)
        self.labelReminder.setAlignment(QtCore.Qt.AlignCenter)

        self.paramListWidget = QListWidget()
        self.paramListWidget.setEnabled(False)
        self.extractParamDict = self.getProtocolExtractionParams()
        for idx, (key, val) in enumerate(self.extractParamDict.items()):
            self.paramListWidget.addItem(str(key) + ": \t" + str(val))

        # Arrange all widgets in the layout
        self.layoutExtract.addWidget(self.labelSignal)
        self.layoutExtract.addWidget(self.fileListWidget)
        self.layoutExtract.addWidget(self.btn_runExtractionScenario)
        self.layoutExtract.addWidget(self.labelReminder)
        self.layoutExtract.addWidget(self.paramListWidget)
        self.layoutExtract.addWidget(self.designerWidget)

        # Add separator...
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        separator.setLineWidth(1)

        self.dlgLayout.addLayout(self.layoutExtract)
        self.dlgLayout.addWidget(separator)

        # -----------------------------------------------------------------------
        # FEATURE VISUALIZATION PART
        self.layoutViz = QVBoxLayout()
        self.layoutViz.setAlignment(QtCore.Qt.AlignTop)
        self.label = QLabel('===== VISUALIZE FEATURES =====')
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.layoutViz.addWidget(self.label)

        self.formLayoutExtract = QFormLayout()

        # LIST OF AVAILABLE SPECTRA WITH CURRENT CLASS
        self.availableSpectraList = QListWidget()
        self.availableSpectraList.setSelectionMode(QListWidget.MultiSelection)
        self.layoutViz.addWidget(self.availableSpectraList)

        self.path1 = ""
        self.path2 = ""

        # Param : fmin for frequency based viz
        self.userFmin = QLineEdit()
        self.userFmin.setText('1')
        self.formLayoutExtract.addRow('frequency min', self.userFmin)
        # Param : fmax for frequency based viz
        self.userFmax = QLineEdit()
        self.userFmax.setText('40')
        self.formLayoutExtract.addRow('frequency max', self.userFmax)

        # Param : Electrode to use for PSD display
        self.electrodePsd = QLineEdit()
        self.electrodePsd.setText('FC1')
        self.formLayoutExtract.addRow('Sensor for PSD visualization', self.electrodePsd)
        # Param : Frequency to use for Topography
        self.freqTopo = QLineEdit()
        self.freqTopo.setText('15')
        self.formLayoutExtract.addRow('Frequency for Topography (Hz)', self.freqTopo)

        self.layoutViz.addLayout(self.formLayoutExtract)

        self.layoutVizButtons = QVBoxLayout()

        self.btn_load_extract = QPushButton("Load spectrum file - extract features")
        self.btn_r2map = QPushButton("Plot Frequency-channel R² map")
        self.btn_timefreq = QPushButton("Plot Time/Freq Analysis")
        self.btn_psd = QPushButton("Plot PSD comparison between classes")
        self.btn_topo = QPushButton("Plot Brain Topography")
        # self.btn_w2map = QPushButton("Plot Wilcoxon Map")
        # self.btn_psd_r2 = QPushButton("Plot PSD comparison between classes")
        self.btn_load_extract.clicked.connect(lambda: self.load_extract())
        self.btn_r2map.clicked.connect(lambda: self.btnR2())
        self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq())
        self.btn_psd.clicked.connect(lambda: self.btnPsd())
        self.btn_topo.clicked.connect(lambda: self.btnTopo())
        # self.btn_w2map.clicked.connect(lambda: self.btnW2())
        # self.btn_psd_r2.clicked.connect(lambda: self.btnpsdR2())

        self.layoutVizButtons.addWidget(self.btn_load_extract)
        self.layoutVizButtons.addWidget(self.btn_r2map)
        self.layoutVizButtons.addWidget(self.btn_psd)
        self.layoutVizButtons.addWidget(self.btn_timefreq)
        self.layoutVizButtons.addWidget(self.btn_topo)
        # self.layoutVizButtons.addWidget(self.btn_w2map)
        # self.layoutVizButtons.addWidget(self.btn_psd_r2)

        self.layoutViz.addLayout(self.layoutVizButtons)

        # Add separator...
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        separator2.setLineWidth(1)

        self.dlgLayout.addLayout(self.layoutViz)
        self.dlgLayout.addWidget(separator2)

        # -----------------------------------------------------------------------
        # FEATURE SELECTION + TRAINING PART
        self.layoutTrain = QVBoxLayout()
        self.layoutTrain.setAlignment(QtCore.Qt.AlignTop)
        self.qvBoxLayouts = [None, None]
        self.qvBoxLayouts[0] = QFormLayout()
        self.qvBoxLayouts[1] = QVBoxLayout()
        self.layoutTrain.addLayout(self.qvBoxLayouts[0])
        self.layoutTrain.addLayout(self.qvBoxLayouts[1])

        self.label2 = QLabel('===== SELECT FEATURES FOR TRAINING =====')
        self.label2.setAlignment(QtCore.Qt.AlignCenter)
        textFeatureSelect = "Ex:\tFCz;14"
        textFeatureSelect = str(textFeatureSelect + "\n\tFCz;14:22 (for freq range)")
        self.label3 = QLabel(textFeatureSelect)
        self.label3.setAlignment(QtCore.Qt.AlignCenter)

        self.qvBoxLayouts[0].addWidget(self.label2)
        self.qvBoxLayouts[0].addWidget(self.label3)

        self.selectedFeats = []
        # Parameter for feat selection/training : First selected pair of Channels / Electrodes
        # We'll add more with a button
        self.selectedFeats.append(QLineEdit())
        self.selectedFeats[0].setText('C4;22')
        pairText = "Feature"
        self.qvBoxLayouts[0].addRow(pairText, self.selectedFeats[0])

        # Param for training
        self.trainingLayout = QFormLayout()
        self.trainingPartitions = QLineEdit()
        self.trainingPartitions.setText(str(10))
        partitionsText = "Number of k-fold for classification"
        self.trainingLayout.addRow(partitionsText, self.trainingPartitions)

        self.fileListWidgetTrain = QListWidget()
        self.fileListWidgetTrain.setSelectionMode(QListWidget.MultiSelection)

        self.btn_addPair = QPushButton("Add feature")
        self.btn_removePair = QPushButton("Remove last feature in the list")
        self.btn_selectFeatures = QPushButton("TRAIN CLASSIFIER using selected files and features")
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair())
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair())
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())

        self.qvBoxLayouts[1].addWidget(self.btn_addPair)
        self.qvBoxLayouts[1].addWidget(self.btn_removePair)
        self.qvBoxLayouts[1].addLayout(self.trainingLayout)
        self.qvBoxLayouts[1].addWidget(self.fileListWidgetTrain)
        self.qvBoxLayouts[1].addWidget(self.btn_selectFeatures)
        self.dlgLayout.addLayout(self.layoutTrain)

        # display initial layout
        self.setLayout(self.dlgLayout)
        self.initialWindow()

        self.refreshLists(os.path.join(self.scriptPath, "generated", "signals"))

        # Timing loop every 2s to get files in working folder
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(4000)  # in milliseconds
        self.timer.timeout.connect(lambda: self.refreshLists(os.path.join(self.scriptPath, "generated", "signals")))
        self.timer.start()

    # -----------------------------------------------------------------------
    # CLASS METHODS
    # -----------------------------------------------------------------------

    def initialWindow(self):
        # ----------
        # Init buttons & fields, set enabled/disabled states in the interface
        # ----------
        self.btn_r2map.setEnabled(False)
        self.btn_timefreq.setEnabled(False)
        self.btn_psd.setEnabled(False)
        self.btn_topo.setEnabled(False)
        # self.btn_w2map.setEnabled(False)
        # self.btn_psd_r2.setEnabled(False)
        self.show()

    def plotWindow(self):
        # ----------
        # Update interface once spectrum/feature files have been read
        # ----------
        self.btn_load_extract.setEnabled(True)
        self.btn_r2map.setEnabled(True)
        self.btn_timefreq.setEnabled(True)
        self.btn_psd.setEnabled(True)
        self.btn_topo.setEnabled(True)
        # self.btn_w2map.setEnabled(True)
        # self.btn_psd_r2.setEnabled(True)
        self.show()

    def refreshLists(self, workingFolder):
        # ----------
        # Refresh all lists. Called once at the init, then once every timer click (see init method)
        # ----------
        self.refreshSignalList(self.fileListWidget, workingFolder)
        self.refreshAvailableSpectraList(workingFolder)
        self.refreshAvailableTrainSignalList(workingFolder)
        return

    def refreshSignalList(self, listwidget, workingFolder):
        # ----------
        # Refresh list of available signal (.ov) files
        # ----------

        # first get a list of all files in workingfolder that match the condition
        filelist = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(".ov"):
                filelist.append(filename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(listwidget.count()-1, 0, -1):
            tempitem = listwidget.item(x).text()
            if tempitem not in filelist:
                listwidget.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range (listwidget.count()):
            items.append(listwidget.item(x).text())
        for filename in filelist:
            if filename not in items:
                listwidget.addItem(filename)
        return

    def refreshAvailableSpectraList(self, signalFolder):
        # ----------
        # Refresh available CSV spectrum files.
        # Only mention current class (set in parameters), and check that both classes are present
        # ----------

        workingFolder = os.path.join(signalFolder, "analysis")
        # self.availableSpectraList.clear()
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]

        # first get a list of all csv files in workingfolder that match the condition
        availableCsvs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str(class1label + ".csv")):
                basename = filename.removesuffix(str(class1label + ".csv"))
                otherClass = str(basename + class2label + ".csv")
                if otherClass in os.listdir(workingFolder):
                    availableCsvs.append(basename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.availableSpectraList.count() - 1, 0, -1):
            tempitem = self.availableSpectraList.item(x).text()
            suffix = str("("+class1label+"/"+class2label+")")
            if tempitem.removesuffix(suffix) not in availableCsvs:
                self.availableSpectraList.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.availableSpectraList.count()):
            items.append(self.availableSpectraList.item(x).text())
        for basename in availableCsvs:
            basenameSuffix = str(basename+"("+class1label+"/"+class2label+")")
            if basenameSuffix not in items:
                self.availableSpectraList.addItem(basenameSuffix)

        return

    def refreshAvailableTrainSignalList(self, signalFolder):
        # ----------
        # Refresh available EDF training files.
        # Only mention current class (set in parameters), and check that both classes are present
        # ----------

        workingFolder = os.path.join(signalFolder, "training")
        # self.availableSpectraList.clear()
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]

        # first get a list of all csv files in workingfolder that match the condition
        availableTrainSigs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str(class1label + ".edf")):
                basename = filename.removesuffix(str(class1label + ".edf"))
                otherClass = str(basename + class2label + ".edf")
                if otherClass in os.listdir(workingFolder):
                    availableTrainSigs.append(basename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.fileListWidgetTrain.count() - 1, 0, -1):
            tempitem = self.fileListWidgetTrain.item(x).text()
            suffix = str("("+class1label+"/"+class2label+")")
            if tempitem.removesuffix(suffix) not in availableTrainSigs:
                self.fileListWidgetTrain.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.fileListWidgetTrain.count()):
            items.append(self.fileListWidgetTrain.item(x).text())
        for basename in availableTrainSigs:
            basenameSuffix = str(basename+"("+class1label+"/"+class2label+")")
            if basenameSuffix not in items:
                self.fileListWidgetTrain.addItem(basenameSuffix)

        return

    def runExtractionScenario(self):
        # ----------
        # Use extraction scenario (sc2-extract-select.xml) to
        # generate CSV files, used for visualization
        # ----------
        if not self.fileListWidget.selectedItems():
            msg = QMessageBox()
            msg.setText("Please select a set of files for feature extraction")
            msg.exec_()
            return

        self.fileListWidget.setEnabled(False)
        self.btn_runExtractionScenario.setEnabled(False)

        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[1])

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # RUN THE SCENARIO FOR ALL SELECTED FILES
        for selectedItem in self.fileListWidget.selectedItems():
            # Modify extraction scenario to use provided signal file,
            # and rename outputs accordingly
            signalFile = selectedItem.text()

            self.btn_runExtractionScenario.setText(str("Processing file : " + signalFile) + "...")

            filename = signalFile.removesuffix(".ov")
            output1 = str(filename + "-" + self.parameterDict["Class1"] + ".csv")
            output2 = str(filename + "-" + self.parameterDict["Class2"] + ".csv")
            outputBaseline1 = str(filename + "-" + self.parameterDict["Class1"] + "-BASELINE.csv")
            outputBaseline2 = str(filename + "-" + self.parameterDict["Class2"] + "-BASELINE.csv")
            outputEdf1 = str(filename + "-" + self.parameterDict["Class1"] + ".edf")
            outputEdf2 = str(filename + "-" + self.parameterDict["Class2"] + ".edf")
            modifyExtractionIO(scenFile, signalFile, output1, output2, outputBaseline1, outputBaseline2, outputEdf1, outputEdf2)

            # Run command (openvibe-designer.cmd --no-gui --play-fast <scen.xml>)
            p = subprocess.Popen([command, "--no-gui", "--play-fast", scenFile],
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


        self.btn_runExtractionScenario.setText(str("Generate Spectrum Files"))
        self.fileListWidget.setEnabled(True)
        self.btn_runExtractionScenario.setEnabled(True)

        self.show()

        return

    def load_extract(self):
        # ----------
        # Load CSV files of selected extracted spectra for visualization
        # ----------
        if not self.availableSpectraList.selectedItems():
            msg = QMessageBox()
            msg.setText("Please select a set of files for analysis")
            msg.exec_()
            return

        self.dataNp1 = []
        self.dataNp2 = []
        self.dataNp1baseline = []
        self.dataNp2baseline = []

        listSampFreq = []

        for selectedItem in self.availableSpectraList.selectedItems():
            selectedSpectra = selectedItem.text()
            class1label = self.parameterDict["Class1"]
            class2label = self.parameterDict["Class2"]
            selectedBasename = selectedSpectra.removesuffix(str("("+class1label+"/"+class2label+")"))

            path1 = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + class1label + ".csv"))
            path2 = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + class2label + ".csv"))
            path1baseline = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + class1label + "-BASELINE.csv"))
            path2baseline = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + class2label + "-BASELINE.csv"))


            data1 = load_csv_cond(path1)
            data2 = load_csv_cond(path2)
            data1baseline = load_csv_cond(path1baseline)
            data2baseline = load_csv_cond(path2baseline)

            # Sampling frequency
            # Infos in the columns header of the CSVs in format "Time:32x251:500"
            # (Column zero contains starting time of the row)
            # 32 is channels, 251 is freq bins, 500 is sampling frequency)
            sampFreq1 = int(data1.columns.values[0].split(":")[-1])
            sampFreq2 = int(data2.columns.values[0].split(":")[-1])
            if sampFreq1 != sampFreq2:
                msg = QMessageBox()
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "sampling frequency mismatch (" + str(sampFreq1) + " vs " + str(sampFreq2) + ")")
                msg.setText(errMsg)
                msg.exec_()
                return

            listSampFreq.append(sampFreq1)

            self.dataNp1.append(data1.to_numpy())
            self.dataNp2.append(data2.to_numpy())
            self.dataNp1baseline.append(data1baseline.to_numpy())
            self.dataNp2baseline.append(data2baseline.to_numpy())

        # Check if all files have the same sampling freq. If not, for now, we don't process further
        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            msg = QMessageBox()
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            msg.setText(errMsg)
            msg.exec_()
            return
        else:
            self.samplingFreq = listSampFreq[0]
            print("Sampling Frequency for selected files : " + str(self.samplingFreq))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.parameterDict["TrialLength"])
        trials = int(self.parameterDict["TrialNb"])
        electrodeListStr = self.parameterDict["ChannelNames"]
        electrodeList = electrodeListStr.split(";")
        nbElectrodes = len(electrodeList)
        n_bins = int((int(self.parameterDict["PsdSize"]) / 2) + 1)
        winLen = float(self.parameterDict["TimeWindowLength"])
        winOverlap = float(self.parameterDict["TimeWindowShift"])

        # For multiple runs (ie. multiple selected CSV files), we just concatenate
        # the trials from all files. Then the displayed spectral features (R²map, PSD, topography)
        # will be computed as averages over all the trials.
        # Time/freq analysis will need a specific process (TODO)
        power_cond1_final = None
        power_cond2_final = None
        power_cond1_baseline_final = None
        power_cond2_baseline_final = None
        timefreq_cond1_final = None
        timefreq_cond2_final = None
        timefreq_cond1_baseline_final = None
        timefreq_cond2_baseline_final = None
        for run in range(len(self.dataNp1)):
            power_cond1, timefreq_cond1 = \
                Extract_CSV_Data(self.dataNp1[run], trialLength, trials, nbElectrodes, n_bins, winLen, winOverlap)
            power_cond2, timefreq_cond2 = \
                Extract_CSV_Data(self.dataNp2[run], trialLength, trials, nbElectrodes, n_bins, winLen, winOverlap)
            power_cond1_baseline, timefreq_cond1_baseline = \
                Extract_CSV_Data(self.dataNp1baseline[run], trialLength, trials, nbElectrodes, n_bins, winLen, winOverlap)
            power_cond2_baseline, timefreq_cond2_baseline = \
                Extract_CSV_Data(self.dataNp2baseline[run], trialLength, trials, nbElectrodes, n_bins, winLen, winOverlap)

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
                timefreq_cond1_baseline_final = np.concatenate((timefreq_cond1_baseline_final, timefreq_cond1_baseline), axis=2)
                timefreq_cond2_baseline_final = np.concatenate((timefreq_cond2_baseline_final, timefreq_cond2_baseline), axis=2)

        trialLengthSec = float(self.parameterDict["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        windowLength = float(self.parameterDict["TimeWindowLength"])
        windowShift = float(self.parameterDict["TimeWindowShift"])
        segmentsPerTrial = round( (trialLength-windowLength) / windowShift )

        timeVectAtomic = [0]
        for i in range(segmentsPerTrial-1):
            timeVectAtomic.append((i+1)*windowShift)

        timeVectAtomic = np.array(timeVectAtomic)
        time_array = np.empty(0)
        idxTrial = 0
        for trial in range(totalTrials):
            time_array = np.concatenate((time_array, timeVectAtomic + (idxTrial*trialLengthSec)) )
            idxTrial += 1

        # Statistical Analysis
        electrodes_orig = channel_generator(nbElectrodes, 'TP9', 'TP10')
        freqs_array = np.arange(0, n_bins)

        Rsigned = Compute_Rsquare_Map_Welch(power_cond2[:, :, :(n_bins-1)], power_cond1[:, :, :(n_bins-1)])
        Wsquare, Wpvalues = Compute_Wilcoxon_Map(power_cond2[:, :, :(n_bins-1)], power_cond1[:, :, :(n_bins-1)])

        Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1, timefreq_cond2 \
            = Reorder_Rsquare(Rsigned, Wsquare, Wpvalues, electrodes_orig, power_cond1, power_cond2, timefreq_cond1, timefreq_cond2)

        self.Features.electrodes_orig = electrodes_orig
        self.Features.power_cond2 = power_cond2_2
        self.Features.power_cond1 = power_cond1_2
        self.Features.timefreq_cond1 = timefreq_cond1
        self.Features.timefreq_cond2 = timefreq_cond2
        # self.Features.time_array = time_array
        self.Features.time_array = timeVectAtomic
        self.Features.freqs_array = freqs_array
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsigned = Rsigned_2
        self.Features.Wsigned = Wsquare_2

        self.Features.average_baseline_cond1 = np.mean(power_cond1_baseline_final, axis=0)
        self.Features.std_baseline_cond1 = np.std(power_cond1_baseline_final, axis=0)
        self.Features.average_baseline_cond2 = np.mean(power_cond2_baseline_final, axis=0)
        self.Features.std_baseline_cond2 = np.std(power_cond2_baseline_final, axis=0)

        self.plotWindow()

    def btnR2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(self.Features.Rsigned,
                       self.Features.freqs_array,
                       self.Features.electrodes_final,
                       self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnW2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(self.Features.Wsigned,
                       self.Features.freqs_array,
                       self.Features.electrodes_final,
                       self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnTimeFreq(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            print("TimeFreq for sensor: " + self.electrodePsd.text())

            # TODO change
            tmin = 0
            tmax = 1.5

            qt_plot_tf(self.Features.timefreq_cond1, self.Features.timefreq_cond2,
                       self.Features.time_array, self.Features.freqs_array,
                       self.electrodePsd.text(), self.fres,
                       self.Features.average_baseline_cond1, self.Features.average_baseline_cond2,
                       self.Features.std_baseline_cond1, self.Features.std_baseline_cond2,
                       self.Features.electrodes_final,
                       int(self.userFmin.text()), int(self.userFmax.text()), float(tmin), float(tmax),
                       self.parameterDict["Class1"], self.parameterDict["Class2"])

            # qt_plot_tf(self.Features.time_right, self.Features.time_left,
            #            self.Features.time_array, self.Features.freqs_array,
            #            self.Features.electrodes_final, self.electrodePsd.text(),
            #            self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnPsd(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            qt_plot_psd(self.Features.power_cond2, self.Features.power_cond1,
                        self.Features.freqs_array, self.Features.electrodes_final,
                        self.electrodePsd.text(),
                        self.fres, int(self.userFmin.text()), int(self.userFmax.text()),
                        self.parameterDict["Class1"], self.parameterDict["Class2"])

    def btnpsdR2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            qt_plot_psd_r2(self.Features.Rsigned,
                           self.Features.power_cond2, self.Features.power_cond1,
                           self.Features.freqs_array, self.Features.electrodes_final,
                           self.electrodePsd.text(),
                           self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnTopo(self):
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.samplingFreq / 2):
            print("Freq Topo: " + self.freqTopo.text())
            qt_plot_topo(self.Features.Rsigned, self.Features.electrodes_final,
                         int(self.freqTopo.text()), self.fres, self.samplingFreq)
        else:
            msg = QMessageBox()
            msg.setText("Invalid frequency for topography")
            msg.exec_()

    def btnAddPair(self):
        self.selectedFeats.append(QLineEdit())
        self.selectedFeats[-1].setText('C4;22')
        self.qvBoxLayouts[0].addRow("Selected Feats Pair", self.selectedFeats[-1])

    def btnRemovePair(self):
        if len(self.selectedFeats) > 1:
            result = self.qvBoxLayouts[0].getWidgetPosition(self.selectedFeats[-1])
            self.qvBoxLayouts[0].removeRow(result[0])
            self.selectedFeats.pop()

    def browseForDesigner(self):
        # ----------
        # Allow user to browse for the "openvibe-designer.cmd" windows cmd
        # ----------
        directory = os.getcwd()
        newPath, dummy = QFileDialog.getOpenFileName(self, "OpenViBE designer", str(directory))
        if "openvibe-designer.cmd" in newPath:
            self.designerTextBox.setText(newPath)
            self.ovScript = newPath

        return

    def btnSelectFeatures(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------

        if not self.fileListWidgetTrain.selectedItems():
            msg = QMessageBox()
            msg.setText("Please select a set of files for training")
            msg.exec_()
            return

        selectedFeats = []

        # Checks :
        # - No empty field
        # - frequencies in acceptable ranges
        # - channels in list
        channelList = self.parameterDict["ChannelNames"].split(";") +self.Features.electrodes_final
        n_bins = int((int(self.parameterDict["PsdSize"]) / 2) + 1)
        for idx, feat in enumerate(self.selectedFeats):
            if feat.text() == "":
                msg = QMessageBox()
                msg.setText("Pair "+str(idx+1)+" is empty...")
                msg.exec_()
                return

            [chan, freqstr] = feat.text().split(";")
            if chan not in channelList:
                msg = QMessageBox()
                msg.setText("Channel in pair " + str(idx + 1) + " (" + str(chan) + ") is not in the list...")
                msg.exec_()
                return

            freqs = freqstr.split(":")
            for freq in freqs:
                if not freq.isdigit():
                    msg = QMessageBox()
                    msg.setText("Frequency in pair " + str(idx + 1) + " (" + str(freq) + ") has an invalid format, must be an integer...")
                    msg.exec_()
                    return
                if int(freq) >= n_bins:
                    msg = QMessageBox()
                    msg.setText("Frequency in pair " + str(idx + 1) + " (" + str(freq) + ") is not in the acceptable range...")
                    msg.exec_()
                    return
            selectedFeats.append(feat.text().split(";"))
            print(feat)

        # FIRST RE-COPY sc2 & sc3 FROM TEMPLATE, SO THE USER CAN DO THIS MULTIPLE TIMES...
        pipelineType = self.parameterDict["pipelineType"]
        templateFolder = settings.optionsTemplatesDir[pipelineType]
        generatedFolder = "generated"

        for i in [2, 3]:
            scenName = settings.templateScenFilenames[i]
            srcFile = os.path.join(self.scriptPath, templateFolder, scenName)
            destFile = os.path.join(self.scriptPath, generatedFolder, scenName)
            print("---Copying file " + srcFile + " to " + destFile)
            copyfile(srcFile, destFile)
            modifyScenarioGeneralSettings(destFile, self.parameterDict)
            if i == 2:
                modifyTrainScenario(selectedFeats, destFile)
            elif i == 3:
                modifyAcqScenario(destFile, self.parameterDict, True)
                modifyOnlineScenario(selectedFeats, destFile)

        # Get training param from GUI and modify training scenario
        err = True
        if self.trainingPartitions.text().isdigit():
            if int(self.trainingPartitions.text()) > 0:
                trainingSize = int(self.trainingPartitions.text())
                err = False
        if err:
            msg = QMessageBox()
            msg.setText("Nb of k-fold should be a positive number")
            msg.exec_()
            return

        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])
        modifyTrainPartitions(trainingSize, scenFile)

        # Create composite file from selected items
        compositeSigList = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            print("Selected file for training: " + selectedItem.text())
            suffix = str("-(" + self.parameterDict["Class1"] + "/" + self.parameterDict["Class2"] + ")")
            filenameWithoutSuffix = selectedItem.text().removesuffix(suffix)
            filenameWithoutSuffix = os.path.basename(filenameWithoutSuffix)
            path = os.path.join(self.scriptPath, "generated", "signals", "training", str(filenameWithoutSuffix))
            compositeSigList.append(path)

        print("Creating composite file, using stimulations " + self.parameterDict["Class1"] + "/" + self.parameterDict["Class2"])
        class1Stim = "OVTK_GDF_Left"
        class2Stim = "OVTK_GDF_Right"
        tmin = 0
        epoch = self.parameterDict["StimulationEpoch"]
        delay = self.parameterDict["StimulationDelay"]
        tmax = float(self.parameterDict["StimulationEpoch"]) - float(self.parameterDict["StimulationDelay"])
        compositeCsv = mergeRuns(compositeSigList, self.parameterDict["Class1"], self.parameterDict["Class2"], class1Stim, class2Stim, tmin, tmax)

        print("Composite file for training: " + compositeCsv)
        compositeCsvBasename = os.path.basename(compositeCsv)
        modifyTrainInput(compositeCsvBasename, scenFile)

        # RUN THE CLASSIFIER TRAINING SCENARIO
        classifierScoreStr = self.runClassifierScenario()

        # PREPARE GOODBYE MESSAGE...
        textGoodbye = "The training scenario using\n\n"
        for i in range(len(selectedFeats)):
            textGoodbye = str(textGoodbye + "  Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
        textGoodbye = str(textGoodbye + "\n... has been generated under:\n\n")
        textGoodbye = str(textGoodbye + os.path.join(self.scriptPath, generatedFolder, settings.templateScenFilenames[2]))
        textGoodbye = str(textGoodbye + "\n\n" + os.path.join(self.scriptPath, generatedFolder, settings.templateScenFilenames[3]))

        textDisplay = classifierScoreStr
        textDisplay = str(textDisplay + "\n\n" + textGoodbye)
        msg = QMessageBox()
        msg.setText(textDisplay)
        msg.setStyleSheet("QLabel{min-width: 1200px;}")
        msg.setWindowTitle("Classifier Training Score")
        msg.exec_()

        return

    def runClassifierScenario(self):
        # ----------
        # Run the classifier training scen (sc2-train.xml), using the provided parameters
        # and features
        # ----------
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # Run actual command (openvibe-designer.cmd --no-gui --play-fast <scen.xml>)
        p = subprocess.Popen([command, "--no-gui", "--play-fast", scenFile],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # Read console output to detect end of process
        # and prompt user with classification score. Quite artisanal but works
        classifierScoreStr = ""
        activateScoreMsgBox = False
        while True:
            output = p.stdout.readline()
            if p.poll() is not None:
                break
            if output:
                print(str(output))
                if "Application terminated" in str(output):
                    break
                if "Cross-validation test" in str(output):
                    activateScoreMsgBox = True
                if activateScoreMsgBox:
                    stringToWrite = str(output).replace("\\r\\n\'", "")
                    stringToWrite = stringToWrite.split("trainer> ")
                    classifierScoreStr = str(classifierScoreStr + stringToWrite[1] + "\n")

        if activateScoreMsgBox:
            classifierScoreStr = str(classifierScoreStr + "\n")
            classifierScoreStr = str(classifierScoreStr + "Results written in file :\n   classifier-weights.xml\n\n")
            classifierScoreStr = str(classifierScoreStr + "If those results are satisfying, you can now open\n   sc3-online.xml")

        return classifierScoreStr

    def getProtocolExtractionParams(self):
        # ----------
        # Get "extraction" parameters from the JSON parameters
        # A bit artisanal, but we'll see if we keep that...
        # ----------
        pipelineKey = self.parameterDict['pipelineType']
        nbParamsExp = settings.scenarioSettingsPartsLength[pipelineKey][0]
        nbParamsExtract = settings.scenarioSettingsPartsLength[pipelineKey][1]

        newDict = {}
        newDict['pipelineType'] = pipelineKey
        newDict['Class1'] = self.parameterDict["Class1"]
        newDict['Class2'] = self.parameterDict["Class2"]
        for idx, param in enumerate(settings.scenarioSettings[pipelineKey]):
            if nbParamsExp <= idx < (nbParamsExp + nbParamsExtract + 1): # print only pipeline-specific
            # if idx < (nbParamsExp + nbParamsExtract + 1): # print all
                newDict[param] = self.parameterDict[param]

        print(newDict)
        return newDict

# ------------------------------------------------------
# STATIC FUNCTIONS
# ------------------------------------------------------
def checkFreqsMinMax(fmin, fmax, fs):
    ok = True
    if not fmin.isdigit() or not fmax.isdigit():
        ok = False
    elif int(fmin) < 0 or int(fmax) < 0:
        ok = False
    elif int(fmin) > (fs/2)+1 or int(fmax) > (fs/2)+1:
        ok = False
    elif int(fmin) >= int(fmax):
        ok = False

    if not ok:
        errorStr = str("fMin and fMax should be numbers between 0 and " + str(fs / 2 + 1))
        errorStr = str(errorStr + "\n and fMin < fMax")
        msg = QMessageBox()
        msg.setText(errorStr)
        msg.exec_()

    return ok

def plot_stats(Rsigned, freqs_array, electrodes, fres, fmin, fmax):
    smoothing  = False
    plot_Rsquare_calcul_welch(Rsigned,np.array(electrodes)[:], freqs_array, smoothing, fres, 10, fmin, fmax)
    plt.show()

def qt_plot_psd_r2(Rsigned, power_cond2, power_cond1, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        msg = QMessageBox()
        msg.setText("No sensor with this name found")
        msg.exec_()
    else:
        plot_psd2(Rsigned, power_cond2, power_cond1, freqs_array, electrodeIdx, electrodesList, 10, fmin, fmax, fres)
        plt.show()

def qt_plot_psd(power_cond2, power_cond1, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        msg = QMessageBox()
        msg.setText("No sensor with this name found")
        msg.exec_()
    else:
        plot_psd(power_cond2, power_cond1, freqs_array, electrodeIdx, electrodesList,
                 10, fmin, fmax, fres, class1label, class2label)
        plt.show()


def qt_plot_topo(Rsigned, electrodes, frequency, fres, fs):
    topo_plot(Rsigned, round(frequency/fres), electrodes, fres, fs, 'Signed R square')
    plt.show()


def qt_plot_tf(timefreq_cond1, timefreq_cond2, time_array, freqs_array, electrode, fres, average_baseline_cond1, average_baseline_cond2, std_baseline_cond1, std_baseline_cond2, electrodes, f_min_var, f_max_var, tmin, tmax, class1label, class2label):
    font = {'family': 'serif',
        'color':  'black',
        'weight': 'normal',
        'size': 14,
        }
    fmin = f_min_var
    fmax = f_max_var
    Test_existing = False
    Index_electrode = 0
    for i in range(len(electrodes)):
        if electrodes[i] == electrode:
            Index_electrode = i
            Test_existing = True

    if Test_existing == False:
        msg = QMessageBox()
        msg.setText("No Electrode with this name found")
        msg.exec_()
    else:
        tf = timefreq_cond1.mean(axis=0)
        tf = np.transpose(tf[Index_electrode, :, :])
        PSD_baseline = average_baseline_cond1[Index_electrode, :]

        A = []
        for i in range(tf.shape[1]):
            A.append(np.divide((tf[:, i]-PSD_baseline), PSD_baseline)*100)
        tf = np.transpose(A)
        vmin = -np.amax(tf)
        vmax = np.amax(tf)
        tlength = tmax-tmin
        time_frequency_map(timefreq_cond1, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10, average_baseline_cond1, electrodes, std_baseline_cond1, vmin, vmax, tlength)
        plt.title('(' + class1label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
        time_frequency_map(timefreq_cond2, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10, average_baseline_cond2, electrodes, std_baseline_cond2, vmin, vmax, tlength)
        plt.title('(' + class2label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
        plt.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

