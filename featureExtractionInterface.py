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

from PyQt5.QtCore import QTimer

from Visualization_Data import *
from featureExtractUtils import *
from modifyOpenvibeScen import *
import bcipipeline_settings as settings

class Features:
    Rsigned = []
    Wsigned = []
    electrodes_orig = []
    electrodes_final = []
    power_right = []
    power_left = []
    freqs_left = []
    time_left = []
    time_right = []
    time_length = []


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
        self.fs = 500

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

        self.dlgLayout.addLayout(self.layoutExtract)

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

        self.layoutVizButtons.addWidget(self.btn_load_extract)
        self.layoutVizButtons.addWidget(self.btn_r2map)
        self.layoutVizButtons.addWidget(self.btn_psd)
        self.layoutVizButtons.addWidget(self.btn_timefreq)
        self.layoutVizButtons.addWidget(self.btn_topo)
        # self.layoutVizButtons.addWidget(self.btn_w2map)
        # self.layoutVizButtons.addWidget(self.btn_psd_r2)

        self.layoutViz.addLayout(self.layoutVizButtons)
        self.dlgLayout.addLayout(self.layoutViz)

        # -----------------------------------------------------------------------
        # FEATURE SELECTION PART
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
        self.trainingPartitions.setEnabled(False)
        partitionsText = "Number of k-fold for classification"
        self.trainingLayout.addRow(partitionsText, self.trainingPartitions)

        self.fileListWidgetTrain = QListWidget()
        # self.fileListWidgetTrain.setSelectionMode(QListWidget.MultiSelection)

        self.btn_addPair = QPushButton("Add feature")
        self.btn_removePair = QPushButton("Remove last feature in the list")
        self.btn_selectFeatures = QPushButton("TRAIN CLASSIFIER using selected files and features")
        # self.btn_runTrain = QPushButton("Run classifier training scenario")

        self.qvBoxLayouts[1].addWidget(self.btn_addPair)
        self.qvBoxLayouts[1].addWidget(self.btn_removePair)
        self.qvBoxLayouts[1].addLayout(self.trainingLayout)
        self.qvBoxLayouts[1].addWidget(self.fileListWidgetTrain)
        self.qvBoxLayouts[1].addWidget(self.btn_selectFeatures)
        # self.qvBoxLayouts[1].addWidget(self.btn_runTrain)
        self.dlgLayout.addLayout(self.layoutTrain)

        # display initial layout
        self.setLayout(self.dlgLayout)
        self.initialWindow()

        self.refreshLists(os.path.join(self.scriptPath, "generated"))

        # Timing loop every 2s to get files in working folder
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(4000)  # in milliseconds
        self.timer.timeout.connect(lambda: self.refreshLists(os.path.join(self.scriptPath, "generated")))
        self.timer.start()

    # -----------------------------------------------------------------------
    # CLASS METHODS
    # -----------------------------------------------------------------------

    def initialWindow(self):
        # ----------
        # Init buttons & fields, set enabled/disabled states in the interface
        # ----------

        self.btn_load_extract.clicked.connect(lambda: self.load_extract())
        # self.btn_runTrain.clicked.connect(lambda: self.runClassifierScenario())

        self.btn_r2map.setEnabled(False)
        # self.btn_w2map.setEnabled(False)
        self.btn_timefreq.setEnabled(False)
        self.btn_psd.setEnabled(False)
        self.btn_topo.setEnabled(False)
        # self.btn_psd_r2.setEnabled(False)
        self.btn_addPair.setEnabled(False)
        self.btn_removePair.setEnabled(False)
        self.btn_selectFeatures.setEnabled(False)
        # self.btn_runTrain.setEnabled(False)
        self.selectedFeats[0].setEnabled(False)
        self.show()

    def plotWindow(self):
        # ----------
        # Update interface once spectrum/feature files have been read
        # ----------

        self.btn_r2map.clicked.connect(lambda: self.btnR2())
        # self.btn_w2map.clicked.connect(lambda: self.btnW2())
        self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq())
        self.btn_psd.clicked.connect(lambda: self.btnPsd())
        self.btn_topo.clicked.connect(lambda: self.btnTopo())
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair())
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair())
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())
        # self.btn_psd_r2.clicked.connect(lambda: self.btnpsdR2())

        self.btn_load_extract.setEnabled(True)
        self.btn_r2map.setEnabled(True)
        # self.btn_w2map.setEnabled(True)
        self.btn_timefreq.setEnabled(True)
        # self.btn_psd_r2.setEnabled(True)
        self.btn_psd.setEnabled(True)
        self.btn_topo.setEnabled(True)

        self.btn_addPair.setEnabled(True)
        self.btn_removePair.setEnabled(True)
        self.selectedFeats[0].setEnabled(True)
        self.trainingPartitions.setEnabled(True)
        self.btn_selectFeatures.setEnabled(True)

        self.show()

    def refreshLists(self, workingFolder):
        # ----------
        # Refresh all lists. Called once at the init, then once every timer click (see init method)
        # ----------
        self.refreshSignalList(self.fileListWidget, workingFolder)
        self.refreshSignalList(self.fileListWidgetTrain, workingFolder)
        self.refreshAvailableSpectraList(workingFolder)
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

    def refreshAvailableSpectraList(self, workingFolder):
        # ----------
        # Refresh available CSV spectrum files.
        # Only mention current class (set in parameters), and check that both classes are present
        # ----------
        
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
            tempitem.removesuffix(str("("+class1label+"/"+class2label+")"))
            if tempitem not in availableCsvs:
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

    def runExtractionScenario(self):
        # ----------
        # Use extraction scenario (sc2-extract-select.xml) to
        # generate CSV files, used for visualization
        # ----------
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
            output1 = str(filename + "-Spectrum-" + self.parameterDict["Class1"] + ".csv")
            output2 = str(filename + "-Spectrum-" + self.parameterDict["Class2"] + ".csv")
            modifyExtractionIO(scenFile, signalFile, output1, output2)

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
        if not self.availableSpectraList.count():
            msg = QMessageBox()
            msg.setText("No available file for analysis")
            msg.exec_()
            return

        self.dataNp1 = []
        self.dataNp2 = []

        listSampFreq = []

        for selectedItem in self.availableSpectraList.selectedItems():
            selectedSpectra = selectedItem.text()
            class1label = self.parameterDict["Class1"]
            class2label = self.parameterDict["Class2"]
            selectedBasename = selectedSpectra.removesuffix(str("("+class1label+"/"+class2label+")"))

            path1 = os.path.join(self.scriptPath, "generated", str(selectedBasename + class1label + ".csv"))
            path2 = os.path.join(self.scriptPath, "generated", str(selectedBasename + class2label + ".csv"))

            data1 = load_csv_cond(path1)
            data2 = load_csv_cond(path2)

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

            # if data1.empty or data2.empty:
            #     msg = QMessageBox()
            #     msg.setText(str("Error loading files " + selectedItem.text() + \
            #                     "Please wait while OpenViBE finishes writing CSV files."))
            #    msg.exec_()
            # else:

            self.dataNp1.append(data1.to_numpy())
            self.dataNp2.append(data2.to_numpy())

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
        time = float(self.parameterDict["TrialLength"])
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
        power_right_final = None
        power_left_final = None
        for run in range(len(self.dataNp1)):
            power_right, power_left, time_left, time_right, time_length = Extract_Data_to_compare(self.dataNp1[run],
                                                                                                  self.dataNp2[run],
                                                                                                  time, trials,
                                                                                                  nbElectrodes,
                                                                                                  n_bins,
                                                                                                  winLen, winOverlap)
            if power_right_final is None:
                power_right_final = power_right
                power_left_final = power_left
            else:
                power_right_final = np.concatenate((power_right_final, power_right))
                power_left_final = np.concatenate((power_left_final, power_left))


        # Statistical Analysis
        electrodes_orig = channel_generator(nbElectrodes, 'TP9', 'TP10')
        freqs_left = np.arange(0, n_bins)

        Rsigned = Compute_Rsquare_Map_Welch(power_right[:, :, :(n_bins-1)], power_left[:, :, :(n_bins-1)])
        Wsquare, Wpvalues = Compute_Wilcoxon_Map(power_right[:, :, :(n_bins-1)], power_left[:, :, :(n_bins-1)])

        Rsigned_2, Wsquare_2, Wpvalues_2, electrodes_final, power_left_2, power_right_2 \
            = Reorder_Rsquare(Rsigned, Wsquare, Wpvalues, electrodes_orig, power_left, power_right)

        # Rsigned_2, electrodes_final, power_left_2, power_right_2 = Reorder_Rsquare(Rsigned, electrodes_orig, power_left, power_right)

        self.Features.electrodes_orig = electrodes_orig
        self.Features.power_right = power_right_2
        self.Features.power_left = power_left_2
        self.Features.time_left = time_left
        self.Features.time_right = time_right
        self.Features.time_length = time_length
        self.Features.freqs_left = freqs_left
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsigned = Rsigned_2
        self.Features.Wsigned = Wsquare_2

        self.plotWindow()

    def btnR2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.fs):
            plot_stats(self.Features.Rsigned,
                       self.Features.freqs_left,
                       self.Features.electrodes_final,
                       self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnW2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.fs):
            plot_stats(self.Features.Wsigned,
                       self.Features.freqs_left,
                       self.Features.electrodes_final,
                       self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnTimeFreq(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.fs):
            print("TimeFreq for sensor: " + self.electrodePsd.text())
            qt_plot_tf(self.Features.time_right, self.Features.time_left,
                       self.Features.time_length, self.Features.freqs_left,
                       self.Features.electrodes_final, self.electrodePsd.text(),
                       self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnPsd(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.fs):
            qt_plot_psd(self.Features.power_right, self.Features.power_left,
                        self.Features.freqs_left, self.Features.electrodes_final,
                        self.electrodePsd.text(),
                        self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnpsdR2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.fs):
            qt_plot_psd_r2(self.Features.Rsigned,
                           self.Features.power_right, self.Features.power_left,
                           self.Features.freqs_left, self.Features.electrodes_final,
                           self.electrodePsd.text(),
                           self.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnTopo(self):
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.fs / 2):
            print("Freq Topo: " + self.freqTopo.text())
            qt_plot_topo(self.Features.Rsigned, self.Features.electrodes_final,
                         int(self.freqTopo.text()), self.fres, self.fs)
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
        selectedFeats = []

        # Checks :
        # - No empty field
        # - frequencies in acceptable ranges
        # - channels in list
        channelList = self.Features.electrodes_final
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

        print("Selected file for training: " + self.fileListWidget.selectedItems()[0].text())
        signalFile = self.fileListWidget.selectedItems()[0].text()
        modifyTrainInput(signalFile, scenFile)

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
        for idx, param in enumerate(settings.scenarioSettings[pipelineKey]):
            if nbParamsExp <= idx < (nbParamsExp + nbParamsExtract + 1):
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

def plot_stats(Rsigned, freqs_left, electrodes, fres, fmin, fmax):
    smoothing  = False
    plot_Rsquare_calcul_welch(Rsigned,np.array(electrodes)[:], freqs_left, smoothing, fres, 10, fmin, fmax)
    plt.show()

def qt_plot_psd_r2(Rsigned, power_right, power_left, freqs_left, electrodesList, electrodeToDisp, fres, fmin, fmax):
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
        plot_psd2(Rsigned, power_right, power_left, freqs_left, electrodeIdx, electrodesList, 10, fmin, fmax, fres)
        plt.show()

def qt_plot_psd(power_right, power_left, freqs_left, electrodesList, electrodeToDisp, fres, fmin, fmax):
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
        plot_psd(power_right, power_left, freqs_left, electrodeIdx, electrodesList, 10, fmin, fmax, fres)
        plt.show()


def qt_plot_topo(Rsigned, electrodes, frequency, fres, fs):
    topo_plot(Rsigned, round(frequency/fres), electrodes, fres, fs, 'Signed R square')
    plt.show()


def qt_plot_tf(timefreq_right, timefreq_left, time_left, freqs_left, electrodesList, electrodeToDisp, fres, fmin, fmax):
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
        time_frequency_map_between_cond(timefreq_right, time_left, freqs_left, electrodeIdx,
                                        fmin, fmax, fres, 10, timefreq_left, electrodesList)
        plt.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

