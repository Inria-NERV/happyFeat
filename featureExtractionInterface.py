import sys
import os
import time
import subprocess
import platform
import json
import numpy as np
import matplotlib.pyplot as plt
from shutil import copyfile
from itertools import chain, combinations

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
from mergeRunsCsv import mergeRunsCsv

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
        self.dataNp1baseline = []
        self.dataNp2baseline = []
        self.Features = Features()

        # Sampling Freq: to be loaded later, in Spectrum CSV files
        self.samplingFreq = None

        self.scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        print(self.scriptPath)
        self.jsonfullpath = os.path.join(self.scriptPath, "generated", "params.json")
        with open(self.jsonfullpath) as jsonfile:
            self.parameterDict = json.load(jsonfile)

        self.ovScript = self.parameterDict["ovDesignerPath"]

        # TODO : get from interface/files !!
        self.fres = 1

        # -----------------------------------------------------------------------
        # CREATE INTERFACE...
        # dlgLayout : Entire Window, separated in horizontal panels
        # Left-most: layoutExtract (for running sc2-extract)
        # Center: Visualization
        # Right-most: Feature Selection & classifier training
        self.setWindowTitle('goodViBEs - Feature Selection interface')
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

        # Label + *editable* list of parameters
        labelExtractParams = str("--- Extraction parameters ---")
        self.labelExtractParams = QLabel(labelExtractParams)
        self.labelExtractParams.setAlignment(QtCore.Qt.AlignCenter)

        self.extractParamsListWidget = QListWidget()
        self.extractParamsListWidget.setEnabled(False)
        self.extractParamsDict = self.getExtractionParameters()
        extractParametersLayout = QHBoxLayout()
        self.layoutExtractLabels = QVBoxLayout()
        self.layoutExtractLineEdits = QVBoxLayout()
        extractParametersLayout.addLayout(self.layoutExtractLabels)
        extractParametersLayout.addLayout(self.layoutExtractLineEdits)
        for idx, (key, val) in enumerate(self.extractParamsDict.items()):
            labelTemp = QLabel()
            labelTemp.setText(str(key))
            self.layoutExtractLabels.addWidget(labelTemp)
            lineEditExtractTemp = QLineEdit()
            lineEditExtractTemp.setText(str(val))
            self.layoutExtractLineEdits.addWidget(lineEditExtractTemp)

        # Label + un-editable list of parameters for reminder
        labelReminder = str("--- Experiment parameters (set in Generator GUI) ---")
        self.labelReminder = QLabel(labelReminder)
        self.labelReminder.setAlignment(QtCore.Qt.AlignCenter)

        self.expParamListWidget = QListWidget()
        self.expParamListWidget.setEnabled(False)
        self.experimentParamsDict = self.getExperimentalParameters()
        minHeight = 0
        for idx, (key, val) in enumerate(self.experimentParamsDict.items()):
            self.expParamListWidget.addItem(str(key) + ": \t" + str(val))
            minHeight += 30

        self.expParamListWidget.setMinimumHeight(minHeight)

        # Generate button
        self.btn_runExtractionScenario = QPushButton("Extract Features and Trials")
        self.btn_runExtractionScenario.clicked.connect(lambda: self.runExtractionScenario())

        # Arrange all widgets in the layout
        self.layoutExtract.addWidget(self.labelSignal)
        self.layoutExtract.addWidget(self.fileListWidget)
        self.layoutExtract.addWidget(self.labelExtractParams)
        self.layoutExtract.addLayout(extractParametersLayout)
        self.layoutExtract.addWidget(self.labelReminder)
        self.layoutExtract.addWidget(self.expParamListWidget)
        self.layoutExtract.addWidget(self.designerWidget)
        self.layoutExtract.addWidget(self.btn_runExtractionScenario)

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

        self.formLayoutVizu = QFormLayout()

        # LIST OF AVAILABLE SPECTRA WITH CURRENT CLASS
        self.availableSpectraList = QListWidget()
        self.availableSpectraList.setSelectionMode(QListWidget.MultiSelection)
        self.layoutViz.addWidget(self.availableSpectraList)

        self.path1 = ""
        self.path2 = ""

        # Param : fmin for frequency based viz
        self.userFmin = QLineEdit()
        self.userFmin.setText('0')
        self.formLayoutVizu.addRow('frequency min', self.userFmin)
        # Param : fmax for frequency based viz
        self.userFmax = QLineEdit()
        self.userFmax.setText('40')
        self.formLayoutVizu.addRow('frequency max', self.userFmax)

        # Param : Electrode to use for PSD display
        self.electrodePsd = QLineEdit()
        self.electrodePsd.setText('C3')
        self.formLayoutVizu.addRow('Sensor for PSD visualization', self.electrodePsd)
        # Param : Frequency to use for Topography
        self.freqTopo = QLineEdit()
        self.freqTopo.setText('12')
        self.formLayoutVizu.addRow('Frequency for Topography (Hz)', self.freqTopo)

        self.layoutViz.addLayout(self.formLayoutVizu)

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
        self.btn_selectFeatures = QPushButton("TRAIN CLASSIFIER using selected runs and features")
        self.btn_allCombinations = QPushButton("FIND BEST COMBINATION of selected runs, using selected features")
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair())
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair())
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())
        self.btn_allCombinations.clicked.connect(lambda: self.btnAllCombinations())

        self.qvBoxLayouts[1].addWidget(self.btn_addPair)
        self.qvBoxLayouts[1].addWidget(self.btn_removePair)
        self.qvBoxLayouts[1].addLayout(self.trainingLayout)
        self.qvBoxLayouts[1].addWidget(self.fileListWidgetTrain)
        self.qvBoxLayouts[1].addWidget(self.btn_selectFeatures)
        self.qvBoxLayouts[1].addWidget(self.btn_allCombinations)
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
        for x in range(listwidget.count()):
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
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]

        # first get a list of all csv files in workingfolder that match the condition
        availableCsvs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str("-" + class1label + ".csv")):
                basename = filename.removesuffix(str("-" + class1label + ".csv"))
                otherClass = str(basename + "-" + class2label + ".csv")
                if otherClass in os.listdir(workingFolder):
                    availableCsvs.append(basename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.availableSpectraList.count() - 1, -1, -1):
            tempitem = self.availableSpectraList.item(x).text()
            suffix = str("-SPECTRUM")
            if tempitem.removesuffix(suffix) not in availableCsvs:
                self.availableSpectraList.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.availableSpectraList.count()):
            items.append(self.availableSpectraList.item(x).text())
        for basename in availableCsvs:
            basenameSuffix = str(basename+"-SPECTRUM")
            if basenameSuffix not in items:
                self.availableSpectraList.addItem(basenameSuffix)

        return

    def refreshAvailableTrainSignalList(self, signalFolder):
        # ----------
        # Refresh available EDF training files.
        # Only mention current class (set in parameters), and check that both classes are present
        # ----------

        workingFolder = os.path.join(signalFolder, "training")

        # first get a list of all csv files in workingfolder that match the condition
        availableTrainSigs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str("-TRIALS.csv")):
                availableTrainSigs.append(filename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.fileListWidgetTrain.count() - 1, -1, -1):
            tempitem = self.fileListWidgetTrain.item(x).text()
            if tempitem not in availableTrainSigs:
                self.fileListWidgetTrain.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.fileListWidgetTrain.count()):
            items.append(self.fileListWidgetTrain.item(x).text())
        for filename in availableTrainSigs:
            if filename not in items:
                self.fileListWidgetTrain.addItem(filename)

        return

    def updateExtractParameters(self):
        # Get new extraction parameters
        # return True if params where changed from last known config
        changed = False
        for idx in range(self.layoutExtractLabels.count()):
            paramLabel = self.layoutExtractLabels.itemAt(idx).widget().text()
            paramValue = self.layoutExtractLineEdits.itemAt(idx).widget().text()
            if paramLabel in self.parameterDict:
                if self.parameterDict[paramLabel] != paramValue:
                    changed = True
                    self.parameterDict[paramLabel] = paramValue

        if changed:
            # update json file
            with open(self.jsonfullpath, "w") as outfile:
                json.dump(self.parameterDict, outfile, indent=4)

        return changed

    def deleteWorkFiles(self):
        path1 = os.path.join(self.scriptPath, "generated", "signals", "analysis")
        path2 = os.path.join(self.scriptPath, "generated", "signals", "training")
        for file in os.listdir(path1):
            if file.endswith('.csv'):
                os.remove(os.path.join(path1, file))
        for file in os.listdir(path2):
            if file.endswith('.csv') or file.endswith('.xml'):
                os.remove(os.path.join(path2, file))
        return

    def runExtractionScenario(self):
        # ----------
        # Use extraction scenario (sc2-extract-select.xml) to
        # generate CSV files, used for visualization
        # ----------

        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[1])

        if not self.fileListWidget.selectedItems():
            myErrorBox("Please select a set of files for feature extraction")
            return

        if self.updateExtractParameters():
            self.deleteWorkFiles()

        modifyScenarioGeneralSettings(scenFile, self.parameterDict)

        # TODO : this doesn't work, doesn't change the display...?
        # self.fileListWidget.setEnabled(False)
        # self.btn_runExtractionScenario.setEnabled(False)

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # RUN THE SCENARIO FOR ALL SELECTED FILES
        for selectedItem in self.fileListWidget.selectedItems():
            # Modify extraction scenario to use provided signal file,
            # and rename outputs accordingly
            signalFile = selectedItem.text()

            # TODO : this doesn't work, doesn't change the display...?
            # self.btn_runExtractionScenario.setText(str("Processing file : " + signalFile) + "...")

            filename = signalFile.removesuffix(".ov")
            outputSpect1 = str(filename + "-" + self.parameterDict["Class1"] + ".csv")
            outputSpect2 = str(filename + "-" + self.parameterDict["Class2"] + ".csv")
            outputBaseline1 = str(filename + "-" + self.parameterDict["Class1"] + "-BASELINE.csv")
            outputBaseline2 = str(filename + "-" + self.parameterDict["Class2"] + "-BASELINE.csv")
            outputTrials = str(filename + "-TRIALS.csv")
            modifyExtractionIO(scenFile, signalFile, outputSpect1, outputSpect2, outputBaseline1, outputBaseline2, outputTrials)

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

        # TODO : this doesn't work, doesn't change the display...?
        # self.btn_runExtractionScenario.setText(str("Extract Features and Trials"))
        # self.fileListWidget.setEnabled(True)
        # self.btn_runExtractionScenario.setEnabled(True)

        self.show()
        return

    def load_extract(self):
        # ----------
        # Load CSV files of selected extracted spectra for visualization
        # We need one CSV file per class, for simplicity...
        # ----------
        if not self.availableSpectraList.selectedItems():
            myErrorBox("Please select a set of files for analysis")
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
            selectedBasename = selectedSpectra.removesuffix(str("-SPECTRUM"))

            path1 = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + "-" + class1label + ".csv"))
            path2 = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                 str(selectedBasename + "-" + class2label + ".csv"))
            path1baseline = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                         str(selectedBasename + "-" + class1label + "-BASELINE.csv"))
            path2baseline = os.path.join(self.scriptPath, "generated", "signals", "analysis",
                                         str(selectedBasename + "-" + class2label + "-BASELINE.csv"))

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
                errMsg = str("Error when loading " + path1 + "\n" + " and " + path2)
                errMsg = str(errMsg + "sampling frequency mismatch (" + str(sampFreq1) + " vs " + str(sampFreq2) + ")")
                myErrorBox(errMsg)
                return

            listSampFreq.append(sampFreq1)

            self.dataNp1.append(data1.to_numpy())
            self.dataNp2.append(data2.to_numpy())
            self.dataNp1baseline.append(data1baseline.to_numpy())
            self.dataNp2baseline.append(data2baseline.to_numpy())

        # Check if all files have the same sampling freq. If not, for now, we don't process further
        if not all(freqsamp == listSampFreq[0] for freqsamp in listSampFreq):
            errMsg = str("Error when loading CSV files\n")
            errMsg = str(errMsg + "Sampling frequency mismatch (" + str(listSampFreq) + ")")
            myErrorBox(errMsg)
            return
        else:
            self.samplingFreq = listSampFreq[0]
            print("Sampling Frequency for selected files : " + str(self.samplingFreq))

        # ----------
        # Compute the features used for visualization
        # ----------
        trialLength = float(self.parameterDict["StimulationEpoch"])
        trials = int(self.parameterDict["TrialNb"])
        electrodeListStr = self.parameterDict["ChannelNames"]
        electrodeList = electrodeListStr.split(";")
        nbElectrodes = len(electrodeList)
        n_bins = int((int(self.parameterDict["PsdSize"]) / 2) + 1)
        winLen = float(self.parameterDict["TimeWindowLength"])
        winShift = float(self.parameterDict["TimeWindowShift"])

        # electrodes_orig = channel_generator(nbElectrodes, 'TP9', 'TP10')
        electrodes_orig = elecGroundRef(electrodeList, 'TP9', 'TP10')
        if not electrodes_orig:
            myErrorBox("Problem with the list of electrodes...")

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
        for run in range(len(self.dataNp1)):
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
                timefreq_cond1_baseline_final = np.concatenate((timefreq_cond1_baseline_final, timefreq_cond1_baseline), axis=2)
                timefreq_cond2_baseline_final = np.concatenate((timefreq_cond2_baseline_final, timefreq_cond2_baseline), axis=2)

        trialLengthSec = float(self.parameterDict["TrialLength"])
        totalTrials = len(self.dataNp1) * trials
        windowLength = float(self.parameterDict["TimeWindowLength"])
        windowShift = float(self.parameterDict["TimeWindowShift"])
        segmentsPerTrial = round((trialLength-windowLength) / windowShift)

        timeVectAtomic = [0]
        for i in range(segmentsPerTrial-1):
            timeVectAtomic.append((i+1)*windowShift)

        timeVectAtomic = np.array(timeVectAtomic)
        time_array = np.empty(0)
        idxTrial = 0
        for trial in range(totalTrials):
            time_array = np.concatenate((time_array, timeVectAtomic + (idxTrial*trialLengthSec)))
            idxTrial += 1

        # Statistical Analysis
        freqs_array = np.arange(0, n_bins)

        Rsigned = Compute_Rsquare_Map_Welch(power_cond2_final[:, :, :(n_bins-1)], power_cond1_final[:, :, :(n_bins-1)])
        Wsquare, Wpvalues = Compute_Wilcoxon_Map(power_cond2_final[:, :, :(n_bins-1)], power_cond1_final[:, :, :(n_bins-1)])

        Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_cond1_2, power_cond2_2, timefreq_cond1_2, timefreq_cond2_2 \
            = Reorder_Rsquare(Rsigned, Wsquare, Wpvalues, electrodes_orig, power_cond1_final, power_cond2_final, timefreq_cond1_final, timefreq_cond2_final)

        self.Features.electrodes_orig = electrodes_orig
        self.Features.power_cond2 = power_cond2_2
        self.Features.power_cond1 = power_cond1_2
        self.Features.timefreq_cond1 = timefreq_cond1_2
        self.Features.timefreq_cond2 = timefreq_cond2_2
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

            tmin = float(self.parameterDict['StimulationDelay'])
            tmax = float(self.parameterDict['StimulationEpoch'])
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]

            qt_plot_tf(self.Features.timefreq_cond1, self.Features.timefreq_cond2,
                       self.Features.time_array, self.Features.freqs_array,
                       self.electrodePsd.text(), self.fres,
                       self.Features.average_baseline_cond1, self.Features.average_baseline_cond2,
                       self.Features.std_baseline_cond1, self.Features.std_baseline_cond2,
                       self.Features.electrodes_final,
                       fmin, fmax, tmin, tmax, class1, class2)

    def btnPsd(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]
            qt_plot_psd(self.Features.power_cond2, self.Features.power_cond1,
                        self.Features.freqs_array, self.Features.electrodes_final,
                        self.electrodePsd.text(),
                        self.fres, fmin, fmax, class1, class2)

    def btnTopo(self):
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.samplingFreq / 2):
            print("Freq Topo: " + self.freqTopo.text())
            qt_plot_topo(self.Features.Rsigned, self.Features.electrodes_final,
                         int(self.freqTopo.text()), self.fres, self.samplingFreq)
        else:
            myErrorBox("Invalid frequency for topography")

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

        # TODO : update json file
        # ...

        return

    def getAndCheckSelectedFeats(self):
        selectedFeats = []
        # Checks :
        # - No empty field
        # - frequencies in acceptable ranges
        # - channels in list
        channelList = self.parameterDict["ChannelNames"].split(";") + self.Features.electrodes_final
        n_bins = int((int(self.parameterDict["PsdSize"]) / 2) + 1)
        for idx, feat in enumerate(self.selectedFeats):
            if feat.text() == "":
                myErrorBox("Pair " + str(idx + 1) + " is empty...")
                return

            [chan, freqstr] = feat.text().split(";")
            if chan not in channelList:
                myErrorBox("Channel in pair " + str(idx + 1) + " (" + str(chan) + ") is not in the list...")
                return

            freqs = freqstr.split(":")
            for freq in freqs:
                if not freq.isdigit():
                    myErrorBox("Frequency in pair " + str(idx + 1) + " (" + str(freq) + ") has an invalid format, must be an integer...")
                    return
                if int(freq) >= n_bins:
                    myErrorBox("Frequency in pair " + str(idx + 1) + " (" + str(freq) + ") is not in the acceptable range...")
                    return
            selectedFeats.append(feat.text().split(";"))
            print(feat)

        return selectedFeats

    def btnSelectFeatures(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------
        if not self.fileListWidgetTrain.selectedItems():
            myErrorBox("Please select a set of files for training")
            return

        selectedFeats = self.getAndCheckSelectedFeats()

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
        trainingSize = 0
        if self.trainingPartitions.text().isdigit():
            if int(self.trainingPartitions.text()) > 0:
                trainingSize = int(self.trainingPartitions.text())
                err = False
        if err:
            myErrorBox("Nb of k-fold should be a positive number")
            return

        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])
        modifyTrainPartitions(trainingSize, scenFile)

        # Create composite file from selected items
        compositeSigList = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            print("Selected file for training: " + selectedItem.text())
            path = os.path.join(self.scriptPath, "generated", "signals", "training", selectedItem.text())
            compositeSigList.append(path)

        class1Stim = "OVTK_GDF_Left"
        class2Stim = "OVTK_GDF_Right"
        tmin = 0
        tmax = float(self.parameterDict["StimulationEpoch"])
        compositeCsv = mergeRunsCsv(compositeSigList, self.parameterDict["Class1"], self.parameterDict["Class2"], class1Stim, class2Stim, tmin, tmax)
        if not compositeCsv:
            myErrorBox("Error merging runs!! Most probably different list of electrodes")

        print("Composite file for training: " + compositeCsv)
        compositeCsvBasename = os.path.basename(compositeCsv)
        newWeightsName = "classifier-weights.xml"
        modifyTrainIO(compositeCsvBasename, newWeightsName, scenFile)

        # RUN THE CLASSIFIER TRAINING SCENARIO
        classifierScoreStr = self.runClassifierScenario()

        # Copy weights file to generated/classifier-weights.xml
        newWeights = os.path.join(self.scriptPath, "generated", "signals", "training", "classifier-weights.xml")
        origFilename = os.path.join(self.scriptPath, "generated", "classifier-weights.xml")
        copyfile(newWeights, origFilename)

        # PREPARE GOODBYE MESSAGE...
        textFeats = str("Using spectral features:\n")
        for i in range(len(selectedFeats)):
            textFeats += str("  Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")

        textGoodbye = str("Results written in file:\t generated/classifier-weights.xml\n")
        textGoodbye += str("If those results are satisfying, you can now open generated/sc3-online.xml in the Designer")

        textDisplay = textFeats
        textDisplay += str("\n" + classifierScoreStr)
        textDisplay += str("\n" + textGoodbye)

        msg = QMessageBox()
        msg.setText(textDisplay)
        msg.setStyleSheet("QLabel{min-width: 600px;}")
        msg.setWindowTitle("Classifier Training Score")
        msg.exec_()

        return

    def btnAllCombinations(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------
        if not self.fileListWidgetTrain.selectedItems():
            myErrorBox("Please select a set of runs for training")
            return
        elif len(self.fileListWidgetTrain.selectedItems()) > 5:
            myErrorBox("Please select 5 runs maximum")
            return

        selectedFeats = self.getAndCheckSelectedFeats()

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
        trainingSize = 0
        if self.trainingPartitions.text().isdigit():
            if int(self.trainingPartitions.text()) > 0:
                trainingSize = int(self.trainingPartitions.text())
                err = False
        if err:
            myErrorBox("Nb of k-fold should be a positive number")
            return

        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])
        modifyTrainPartitions(trainingSize, scenFile)

        # Create list of files from selected items
        compositeSigList = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            print("Selected file for training: " + selectedItem.text())
            path = os.path.join(self.scriptPath, "generated", "signals", "training", selectedItem.text())
            compositeSigList.append(path)

        combinationsList = list(myPowerset(compositeSigList))
        sigIdxList = range(len(compositeSigList))
        combIdx = list(myPowerset(sigIdxList))
        scores = [0 for x in range(len(combIdx))]

        class1Stim = "OVTK_GDF_Left"
        class2Stim = "OVTK_GDF_Right"
        tmin = 0
        tmax = float(self.parameterDict["StimulationEpoch"]) - float(self.parameterDict["StimulationDelay"])

        for idxcomb, comb in enumerate(combinationsList):
            sigList = []
            for file in comb:
                sigList.append(file)
            compositeCsv = mergeRunsCsv(sigList, self.parameterDict["Class1"], self.parameterDict["Class2"], class1Stim, class2Stim, tmin, tmax)
            if not compositeCsv:
                myErrorBox("Error merging runs!! Most probably different list of electrodes")

            print("Composite file for training: " + compositeCsv)
            compositeCsvBasename = os.path.basename(compositeCsv)
            newWeightsName = str("classifier-weights-" + str(idxcomb) + ".xml")
            modifyTrainIO(compositeCsvBasename, newWeightsName, scenFile)

            # RUN THE CLASSIFIER TRAINING SCENARIO
            classifierScoreStr = self.runClassifierScenario()
            scores[idxcomb] = float(classifierScoreStr.split("is ")[1].split("%")[0])

        # Find max score
        maxIdx = scores.index(max(scores))
        # Copy weights file to generated/classifier-weights.xml
        maxFilename = os.path.join(self.scriptPath, "generated", "signals", "training", "classifier-weights-")
        maxFilename += str(str(maxIdx) + ".xml")
        origFilename = os.path.join(self.scriptPath, "generated", "classifier-weights.xml")
        copyfile(maxFilename, origFilename)

        # ==========================
        # PREPARE GOODBYE MESSAGE...
        textFeats = str("Using spectral features:\n")
        for i in range(len(selectedFeats)):
            textFeats += str("\tChannel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1]) + " Hz\n")
        textFeats += str("\n... and experiment runs:\n")
        for i in range(len(compositeSigList)):
            textFeats += str("\t[" + str(i) + "]: " + os.path.basename(compositeSigList[i]) + "\n")

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

        textGoodbye = str("The weights for this combination have been written to:\n")
        textGoodbye += str("\tgenerated/classifier-weights.xml\n")
        textGoodbye += str("If those results are satisfying, you can now open this scenario in the Designer:\n")
        textGoodbye += str("\tgenerated/sc3-online.xml")

        textDisplay = textFeats
        textDisplay = str(textDisplay + "\n" + textScore)
        textDisplay = str(textDisplay + "\n" + textGoodbye)
        msg = QMessageBox()
        msg.setText(textDisplay)
        msg.setStyleSheet("QLabel{min-width: 600px;}")
        msg.setWindowTitle("Classifier Training Score")
        msg.exec_()

        return

    def runClassifierScenario(self):
        # ----------
        # Run the classifier training scen (sc2-train.xml), using the provided parameters
        # and features
        # ----------
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])

        # TODO WARNING : MAYBE CHANGE THAT IN THE FUTURE...
        enableConfChange = False
        if enableConfChange:
            # CHECK IF openvibe.conf has randomization of k-fold enabled
            # if not, change it
            confFile = os.path.join(os.path.dirname(self.ovScript), "share", "openvibe", "kernel", "openvibe.conf")
            if platform.system() == 'Windows':
                confFile = confFile.replace("/", "\\")
            modifyConf = False
            with open(confFile, 'r') as conf:
                confdata = conf.read()
                if "Plugin_Classification_RandomizeKFoldTestData = false" in confdata:
                    modifyConf = True
                    confdata = confdata.replace("Plugin_Classification_RandomizeKFoldTestData = false", "Plugin_Classification_RandomizeKFoldTestData = true")
            if modifyConf:
                with open(confFile, 'w') as conf:
                    conf.write(confdata)

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
                    classifierScoreStr = str(classifierScoreStr+"\n")
                    break
                if "Cross-validation test" in str(output):
                    activateScoreMsgBox = True
                if activateScoreMsgBox:
                    stringToWrite = str(output).replace("\\r\\n\'", "")
                    stringToWrite = stringToWrite.split("trainer> ")
                    classifierScoreStr = str(classifierScoreStr + stringToWrite[1] + "\n")

        return classifierScoreStr

    def getExperimentalParameters(self):
        # ----------
        # Get experimental parameters from the JSON parameters
        # ----------
        newDict = {'Pipeline': self.parameterDict['pipelineType'],
                   'Class 1': self.parameterDict["Class1"],
                   'Class 2': self.parameterDict["Class2"],
                   'Trial Length': self.parameterDict["TrialLength"],
                   'Pre Stimulus Time': self.parameterDict["TrialWait"]}

        return newDict

    def getExtractionParameters(self):
        # ----------
        # Get "extraction" parameters from the JSON parameters
        # A bit artisanal, but we'll see if we keep that...
        # ----------
        pipelineKey = self.parameterDict['pipelineType']
        nbParamsExp = settings.scenarioSettingsPartsLength[pipelineKey][0]
        nbParamsExtract = settings.scenarioSettingsPartsLength[pipelineKey][1]

        newDict = {}
        for idx, param in enumerate(settings.scenarioSettings[pipelineKey]):
            if nbParamsExp <= idx < (nbParamsExp + nbParamsExtract + 1):  # print only pipeline-specific
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
        myErrorBox(errorStr)

    return ok

def plot_stats(Rsigned, freqs_array, electrodes, fres, fmin, fmax):
    smoothing = False
    plot_Rsquare_calcul_welch(Rsigned, np.array(electrodes)[:], freqs_array, smoothing, fres, 10, fmin, fmax)
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
        myErrorBox("No sensor with this name found")
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

    if not Test_existing:
        myErrorBox("No Electrode with this name found")
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

def myPowerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(1, len(s)+1))

def myErrorBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.exec_()
    return


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())
