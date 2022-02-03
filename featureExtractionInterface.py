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
        # dlgLayoutMeta : Entire Window, separated in 2 Vertical zones.
        # Top vertical zone : extractLayout (for running sc2-extract)
        # Bottom vertical zone : dlgLayout, 2 Horizontal pannels
        # - Left Pannel : Visualization
        # - Right Pannel : Feature Selection & classifier training        
        self.setWindowTitle('goodViBEs - Feature Selection Interface')
        self.dlgLayoutMeta = QVBoxLayout()
        self.extractLayout = QVBoxLayout()
        self.dlgLayout = QHBoxLayout()        
        self.dlgLayoutMeta.addLayout(self.extractLayout)
        self.dlgLayoutMeta.addLayout(self.dlgLayout)

        # -----------------------------------------------------------------------

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
        self.extractLayout.addWidget(self.designerWidget)

        # FILE LOADING (from .ov file(s)) 
        # AND RUNNING SCENARIO FOR SPECTRA EXTRACTION
        labelSignal = str("===== Feature extraction from signal files =====")
        self.labelSignal = QLabel(labelSignal)
        self.labelSignal.setAlignment(QtCore.Qt.AlignCenter)

        self.fileListWidget = QListWidget()
        self.fileListWidget.setSelectionMode(QListWidget.MultiSelection)
        self.refreshSignalList()

        # Refresh button
        self.btn_refreshSignalList = QPushButton("Refresh list")
        self.btn_refreshSignalList.clicked.connect(lambda: self.refreshSignalList())

        # Generate button
        self.btn_runExtractionScenario = QPushButton("Generate Spectrum Files")
        self.btn_runExtractionScenario.clicked.connect(lambda: self.runExtractionScenario())

        self.extractLayout.addWidget(self.labelSignal)
        self.extractLayout.addWidget(self.fileListWidget)
        self.extractLayout.addWidget(self.btn_refreshSignalList)
        self.extractLayout.addWidget(self.btn_runExtractionScenario)

        # -----------------------------------------------------------------------
        # FEATURE VISUALIZATION PART
        self.layoutLeft = QVBoxLayout()
        self.layoutLeft.setAlignment(QtCore.Qt.AlignTop)
        self.label = QLabel('===== VISUALIZE FEATURES =====')
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.layoutLeft.addWidget(self.label)

        self.formLayoutExtract = QFormLayout()

        # LIST OF AVAILABLE SPECTRA WITH CURRENT CLASS
        self.availableSpectraList = QListWidget()
        self.availableSpectraList.setSelectionMode(QListWidget.MultiSelection)
        self.refreshAvailableSpectraList()

        self.btn_refreshSpectraList = QPushButton("Refresh list")
        self.btn_refreshSpectraList.clicked.connect(lambda: self.refreshAvailableSpectraList())

        self.layoutLeft.addWidget(self.availableSpectraList)
        self.layoutLeft.addWidget(self.btn_refreshSpectraList)

        self.path1 = ""
        self.path2 = ""

        # self.path1 = QLineEdit()
        # pathSpectrum1 = os.path.join(self.scriptPath, "generated", "spectrumAmplitude-Left.csv")
        # self.path1.setText(pathSpectrum1)
        # self.formLayoutExtract.addRow('Class 1 path:', self.path1)
        # Param : Path 2
        # self.path2 = QLineEdit()
        # pathSpectrum2 = os.path.join(self.scriptPath, "generated", "spectrumAmplitude-Right.csv")
        # self.path2.setText(pathSpectrum2)
        # self.formLayoutExtract.addRow('Class 2 path:', self.path2)

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

        self.layoutLeft.addLayout(self.formLayoutExtract)

        self.layoutLeftButtons = QVBoxLayout()

        self.btn_load_extract = QPushButton("Load spectrum file - extract features")
        self.btn_r2map = QPushButton("Plot Frequency-channel R² map")
        self.btn_timefreq = QPushButton("Plot Time/Freq Analysis")
        self.btn_psd = QPushButton("Plot PSD comparison between classes")
        self.btn_topo = QPushButton("Plot Brain Topography")
        # self.btn_w2map = QPushButton("Plot Wilcoxon Map")
        # self.btn_psd_r2 = QPushButton("Plot PSD comparison between classes")

        self.layoutLeftButtons.addWidget(self.btn_load_extract)
        self.layoutLeftButtons.addWidget(self.btn_r2map)
        self.layoutLeftButtons.addWidget(self.btn_psd)
        self.layoutLeftButtons.addWidget(self.btn_timefreq)
        self.layoutLeftButtons.addWidget(self.btn_topo)
        # self.layoutLeftButtons.addWidget(self.btn_w2map)
        # self.layoutLeftButtons.addWidget(self.btn_psd_r2)

        self.layoutLeft.addLayout(self.layoutLeftButtons)
        self.dlgLayout.addLayout(self.layoutLeft)

        # -----------------------------------------------------------------------
        # FEATURE SELECTION PART
        self.layoutRight = QVBoxLayout()
        self.layoutRight.setAlignment(QtCore.Qt.AlignTop)
        self.qvBoxLayouts = [None, None]
        self.qvBoxLayouts[0] = QFormLayout()
        self.qvBoxLayouts[1] = QVBoxLayout()
        self.layoutRight.addLayout(self.qvBoxLayouts[0])
        self.layoutRight.addLayout(self.qvBoxLayouts[1])

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

        self.btn_addPair = QPushButton("Add feature")
        self.btn_removePair = QPushButton("Remove last feature in the list")
        self.btn_selectFeatures = QPushButton("Validate selection -- TRAIN CLASSIFIER")
        # self.btn_runTrain = QPushButton("Run classifier training scenario")

        self.qvBoxLayouts[1].addWidget(self.btn_addPair)
        self.qvBoxLayouts[1].addWidget(self.btn_removePair)
        self.qvBoxLayouts[1].addLayout(self.trainingLayout)
        self.qvBoxLayouts[1].addWidget(self.btn_selectFeatures)
        # self.qvBoxLayouts[1].addWidget(self.btn_runTrain)
        self.dlgLayout.addLayout(self.layoutRight)

        # display initial layout
        self.setLayout(self.dlgLayoutMeta)
        self.initialWindow()

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

    def refreshSignalList(self):
        self.fileListWidget.clear()
        for filename in os.listdir(os.path.join(self.scriptPath, "generated")):
            if filename.endswith(".ov"):
                self.fileListWidget.addItem(filename)
        return

    def refreshAvailableSpectraList(self):
        self.availableSpectraList.clear()
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]
        for filename in os.listdir(os.path.join(self.scriptPath, "generated")):
            if filename.endswith(str(class1label + ".csv")):
                otherClass = filename.removesuffix(str(class1label + ".csv"))
                otherClass = str(otherClass + class2label + ".csv")
                if otherClass in os.listdir(os.path.join(self.scriptPath, "generated")):
                    available = filename.removesuffix(str(class1label + ".csv"))
                    self.availableSpectraList.addItem(str(available + "(" + class1label + "/" + class2label + ")"))

        if self.availableSpectraList.count():
            self.availableSpectraList.setCurrentRow(0)

        return

    def runExtractionScenario(self):
        # ----------
        # Use extraction scenario (sc2-extract-select.xml) to
        # generate CSV files, used for visualization
        # ----------
        self.fileListWidget.setEnabled(False)
        self.btn_refreshSignalList.setEnabled(False)
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
        self.btn_refreshSignalList.setEnabled(True)
        self.btn_runExtractionScenario.setEnabled(True)

        self.refreshAvailableSpectraList()

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

        for selectedItem in self.availableSpectraList.selectedItems():
            selectedSpectra = selectedItem.text()
            class1label = self.parameterDict["Class1"]
            class2label = self.parameterDict["Class2"]
            selectedBasename = selectedSpectra.removesuffix(str("("+class1label+"/"+class2label+")"))

            path1 = os.path.join(self.scriptPath, "generated", str(selectedBasename + class1label + ".csv"))
            path2 = os.path.join(self.scriptPath, "generated", str(selectedBasename + class2label + ".csv"))

            data1 = load_csv_cond(path1)
            data2 = load_csv_cond(path2)

            # if data1.empty or data2.empty:
            #     msg = QMessageBox()
            #     msg.setText(str("Error loading files " + selectedItem.text() + \
            #                     "Please wait while OpenViBE finishes writing CSV files."))
            #    msg.exec_()
            # else:

            self.dataNp1.append(data1.to_numpy())
            self.dataNp2.append(data2.to_numpy())

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
        directory = os.getcwd()
        newPath, dummy = QFileDialog.getOpenFileName(self, "OpenViBE designer", str(directory))
        if "openvibe-designer.cmd" in newPath:
            self.designerTextBox.setText(newPath)
            self.ovScript = newPath

        return

    def btnSelectFeatures(self):
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
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[2])

        # BUILD THE COMMAND (use designer.cmd from GUI)
        command = self.ovScript
        if platform.system() == 'Windows':
            command = command.replace("/", "\\")

        # For debugging purposes
        printCommand = True
        if printCommand:
            cmd = str(self.ovScript.replace("/", "\\") + " --no-gui --play-fast ")
            cmd = str(cmd + str(scenFile))
            print(cmd)

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

