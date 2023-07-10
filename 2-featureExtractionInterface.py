import sys
import os
import time
import subprocess
import platform
import json
import numpy as np
import matplotlib.pyplot as plt

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QMenuBar
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QAction

from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer

from Visualization_Data import *
from featureExtractUtils import *
from modifyOpenvibeScen import *
from utils import myPowerset
from workThreads import *
from myProgressBar import ProgressBar, ProgressBarNoInfo

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

    connect_cond1 = []
    connect_cond2 = []

    freqs_array = []
    time_array = []
    fres = []

    average_baseline_cond1 = []
    std_baseline_cond1 = []
    average_baseline_cond2 = []
    std_baseline_cond2 = []

    samplingFreq = []


class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        # ---------------
        # INITIALIZATIONS
        # ---------------
        self.dataNp1 = []
        self.dataNp2 = []
        self.dataNp1baseline = []
        self.dataNp2baseline = []
        self.Features = Features()
        self.Features2 = Features()
        self.plotBtnsEnabled = False
        self.trainingFiles = []
        # Sampling Freq: to be loaded later, in CSV files
        self.samplingFreq = None
        self.ovScript = None
        self.sensorMontage = None
        self.customMontagePath = None

        self.extractTimerStart = 0
        self.extractTimerEnd = 0
        self.vizTimerStart = 0
        self.vizTimerEnd = 0
        self.trainTimerStart = 0
        self.trainTimerEnd = 0

        # Work Threads & Progress bars
        self.acquisitionThread = None
        self.extractThread = None
        self.loadFilesForVizThread = None
        self.loadFilesForVizThread2 = None
        self.trainClassThread = None
        self.progressBarExtract = None
        self.progressBarViz = None
        self.progressBarViz2 = None
        self.progressBarTrain = None

        # GET PARAMS FROM JSON FILE
        self.scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))

        if "params.json" in os.listdir(os.path.join(self.scriptPath, "generated")):
            print("--- Using parameters from params.json...")
            self.jsonfullpath = os.path.join(self.scriptPath, "generated", "params.json")
            with open(self.jsonfullpath) as jsonfile:
                self.parameterDict = json.load(jsonfile)
            self.ovScript = self.parameterDict["ovDesignerPath"]
            self.sensorMontage = self.parameterDict["sensorMontage"]
            self.customMontagePath = self.parameterDict["customMontagePath"]
        else:
            # WARN and exit
            myMsgBox("--- WARNING : no params.json found, please use 1-bcipipeline_qt.py first !")
            self.reject()

        # -----------------------------------------------------------------------
        # CREATE INTERFACE...
        # dlgLayout : Entire Window, separated in horizontal panels
        # Left-most: layoutExtract (for running sc2-extract)
        # Center: Visualization
        # Right-most: Feature Selection & classifier training
        self.setWindowTitle('HappyFeat - Feature Selection interface')
        self.dlgLayout = QHBoxLayout()

        # Create top bar menus...
        self.menuBar = QMenuBar(self)
        self.dlgLayout.setMenuBar(self.menuBar)
        self.menuOptions = QMenu("&Options")
        self.menuBar.addMenu(self.menuOptions)
        # OpenViBE designer browser...
        self.qActionFindOV = QAction("&Browse for OpenViBE", self)
        self.qActionFindOV.triggered.connect(lambda: self.browseForDesigner())
        self.menuOptions.addAction(self.qActionFindOV)

        # # JSON params...
        # self.qActionLoadJson = QAction("&Load param file", self)
        # self.qActionLoadJson.triggered.connect(lambda: self.loadJsonFile())
        # self.menuOptions.addAction(self.qActionLoadJson)

        # -----------------------------------------------------------------------
        # NEW! LEFT-MOST PART: Signal acquisition & Online classification parts

        self.layoutAcqOnline = QVBoxLayout()
        self.layoutAcqOnline.setAlignment(QtCore.Qt.AlignTop)

        # Top label...
        labelAcqOnline = str("== ACQUISITION ==")
        self.labelAcqOnline = QLabel(labelAcqOnline)
        self.labelAcqOnline.setAlignment(QtCore.Qt.AlignCenter)
        self.labelAcqOnline.setAlignment(QtCore.Qt.AlignTop)
        self.labelAcqOnline.setFont(QFont("system-ui", 12))
        self.labelAcqOnline.setStyleSheet("font-weight: bold")

        # Acquisition button
        self.btn_runAcquisitionScenario = QPushButton("Run Acquisition Scenario")
        self.btn_runAcquisitionScenario.clicked.connect(lambda: self.runAcquisitionScenario())
        self.btn_runAcquisitionScenario.setStyleSheet("font-weight: bold")

        # Add separator...
        separatorLeft = QFrame()
        separatorLeft.setFrameShape(QFrame.VLine)
        separatorLeft.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        separatorLeft.setLineWidth(1)

        self.layoutAcqOnline.addWidget(self.labelAcqOnline)
        self.layoutAcqOnline.addWidget(self.btn_runAcquisitionScenario, alignment=QtCore.Qt.AlignVCenter)

        # TODO : include that later in the interface...
        #self.dlgLayout.addLayout(self.layoutAcqOnline, 1)
        #self.dlgLayout.addWidget(separatorLeft)

        # -----------------------------------------------------------------------
        # LEFT PART : Extraction from signal files (sc2-extract.xml)
        # FILE LOADING (from .ov file(s))
        # AND RUNNING SCENARIO FOR DATA EXTRACTION

        self.layoutExtract = QVBoxLayout()
        self.layoutExtract.setAlignment(QtCore.Qt.AlignTop)

        # Top label...
        labelFeatExtract = str("== FEATURE EXTRACTION ==")
        self.labelFeatExtract = QLabel(labelFeatExtract)
        self.labelFeatExtract.setAlignment(QtCore.Qt.AlignCenter)
        self.labelFeatExtract.setFont(QFont("system-ui", 12))
        self.labelFeatExtract.setStyleSheet("font-weight: bold")

        self.fileListWidget = QListWidget()
        self.fileListWidget.setSelectionMode(QListWidget.MultiSelection)

        # Label + *editable* list of parameters
        labelExtractParams = str("--- Extraction parameters ---")
        self.labelExtractParams = QLabel(labelExtractParams)
        self.labelExtractParams.setAlignment(QtCore.Qt.AlignCenter)

        # Copy extraction parameters from json file.
        # First create a new dict (extractParamsDict) with defaults params...
        self.extractParamsDict = self.getExtractionParameters()
        # ... then copy from existing params file
        if self.parameterDict:
            for (key, elem) in enumerate(self.extractParamsDict):
                if elem in self.parameterDict:
                    self.extractParamsDict[elem] = self.parameterDict[elem]

        extractParametersLayout = QHBoxLayout()
        self.layoutExtractLabels = QVBoxLayout()
        self.layoutExtractLineEdits = QVBoxLayout()
        extractParametersLayout.addLayout(self.layoutExtractLabels)
        extractParametersLayout.addLayout(self.layoutExtractLineEdits)

        # For each extraction param of the selected metric (see bcipipeline_settings.py)
        # add a widget allowing the user to edit this parameter
        for idx, (paramId, paramVal) in enumerate(self.extractParamsDict.items()):
            labelTemp = QLabel()
            labelTemp.setText(settings.paramIdText[paramId])
            self.layoutExtractLabels.addWidget(labelTemp)
            # special case : combobox for connectivity metric
            if paramId == "ConnectivityMetric":
                metricCombo = QComboBox(self)
                connectIdx = 0
                for idxMetric, key in enumerate(settings.connectMetricsComboText):
                    metricCombo.addItem(settings.connectMetricsComboText[key], idxMetric)
                    # if current metric is the one in the params, save the idx
                    # in order to set the combobox to this value
                    if self.extractParamsDict["ConnectivityMetric"] == settings.connectMetrics[idxMetric]:
                        connectIdx = idxMetric

                metricCombo.setCurrentIndex(connectIdx)
                self.layoutExtractLineEdits.addWidget(metricCombo)
            else:
                lineEditExtractTemp = QLineEdit()
                lineEditExtractTemp.setText(self.parameterDict[paramId])
                self.layoutExtractLineEdits.addWidget(lineEditExtractTemp)

        # Label + un-editable list of parameters for reminder
        labelReminder = str("--- Experiment parameters (set in Generator GUI) ---")
        self.labelReminder = QLabel(labelReminder)
        self.labelReminder.setAlignment(QtCore.Qt.AlignCenter)

        self.expParamListWidget = QPlainTextEdit()
        self.expParamListWidget.setReadOnly(True)
        self.expParamListWidget.setStyleSheet("background-color: rgb(200,200,200)")
        self.experimentParamsDict = self.getExperimentalParameters()
        minHeight = 0
        for idx, (paramId, paramVal) in enumerate(self.experimentParamsDict.items()):
            self.expParamListWidget.insertPlainText(settings.paramIdText[paramId] + ": \t" + str(paramVal) + "\n")
            minHeight += 16
        self.expParamListWidget.setMinimumHeight(minHeight)

        # Extraction button
        self.btn_runExtractionScenario = QPushButton("Extract Features and Trials")
        self.btn_runExtractionScenario.clicked.connect(lambda: self.runExtractionScenario())
        self.btn_runExtractionScenario.setStyleSheet("font-weight: bold")

        # NOTE : THIS HAS BEEN MOVED TO "OPTIONS" MENU IN TOP BAR
        # # TODO : keep this part ? OPENVIBE DESIGNER FINDER
        # self.btn_browseOvScript = QPushButton("Browse for OpenViBE designer script")
        # self.btn_browseOvScript.clicked.connect(lambda: self.browseForDesigner())
        # self.designerWidget = QWidget()
        # layout_designer_h = QHBoxLayout(self.designerWidget)
        # self.designerTextBox = QLineEdit()
        # self.designerTextBox.setText(str(self.ovScript))
        # self.designerTextBox.setEnabled(False)
        # layout_designer_h.addWidget(self.designerTextBox)
        # layout_designer_h.addWidget(self.btn_browseOvScript)

        # Arrange all widgets in the layout
        self.layoutExtract.addWidget(self.labelFeatExtract)
        self.layoutExtract.addWidget(self.fileListWidget)
        self.layoutExtract.addWidget(self.labelExtractParams)
        self.layoutExtract.addLayout(extractParametersLayout)
        self.layoutExtract.addWidget(self.labelReminder)
        self.layoutExtract.addWidget(self.expParamListWidget)
        # self.layoutExtract.addWidget(self.designerWidget)
        self.layoutExtract.addWidget(self.btn_runExtractionScenario)

        # Add separator...
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        separator.setLineWidth(1)

        # Add all this to the "general" Layout
        self.dlgLayout.addLayout(self.layoutExtract, 1)
        self.dlgLayout.addWidget(separator)

        # -----------------------------------------------------------------------
        # CENTRAL PART : FEATURE VISUALIZATION PART
        # SELECT DATA TO ANALYZE (from .csv file(s) generated through Extraction)
        # PROVIDE PLOTTING OPTIONS

        self.layoutViz = QVBoxLayout()
        self.layoutViz.setAlignment(QtCore.Qt.AlignTop)
        self.labelViz = QLabel('== VISUALIZE FEATURES ==')
        self.labelViz.setFont(QFont("system-ui", 12))
        self.labelViz.setStyleSheet("font-weight: bold")
        self.labelViz.setAlignment(QtCore.Qt.AlignCenter)
        self.layoutViz.addWidget(self.labelViz)

        # LIST OF AVAILABLE ANALYSIS FILES WITH CURRENT CLASS
        self.availableFilesForVizList = QListWidget()
        self.availableFilesForVizList.setSelectionMode(QListWidget.MultiSelection)
        self.layoutViz.addWidget(self.availableFilesForVizList)

        # Button to load files...
        self.btn_loadFilesForViz = QPushButton("Load file(s) for analysis")
        self.btn_loadFilesForViz.clicked.connect(lambda: self.loadFilesForViz())
        self.btn_loadFilesForViz.setStyleSheet("font-weight: bold")
        self.layoutViz.addWidget(self.btn_loadFilesForViz)

        # LIST OF PARAMETERS FOR VISUALIZATION
        self.formLayoutViz = QFormLayout()

        # COMMON PARAMETERS... TODO : put those in dictionaries to make everything more flexible
        # Param : fmin for frequency based viz
        self.userFmin = QLineEdit()
        self.userFmin.setText('0')
        self.formLayoutViz.addRow('Frequency min', self.userFmin)
        # Param : fmax for frequency based viz
        self.userFmax = QLineEdit()
        self.userFmax.setText('40')
        self.formLayoutViz.addRow('Frequency max', self.userFmax)
        # Param : Electrode to use for PSD display
        self.electrodePsd = QLineEdit()
        self.electrodePsd.setText('CP3')
        self.formLayoutViz.addRow('Sensor for PSD visualization', self.electrodePsd)
        # Param : Frequency to use for Topography
        self.freqTopo = QLineEdit()
        self.freqTopo.setText('12')
        self.formLayoutViz.addRow('Topography Freq (Hz), use \":\" for freq band', self.freqTopo)
        # Param : checkbox for colormap scaling
        self.colormapScale = QCheckBox()
        self.colormapScale.setTristate(False)
        self.colormapScale.setChecked(True)
        self.formLayoutViz.addRow('Scale Colormap (R²map and Topography)', self.colormapScale)

        self.layoutViz.addLayout(self.formLayoutViz)

        # Buttons for visualizations...
        # TODO : make it more flexible...
        self.parallelVizLayouts = [None, None]
        self.parallelVizLayouts[0] = QVBoxLayout()
        self.parallelVizLayouts[1] = QVBoxLayout()

        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            # Viz options for "Spectral Power" pipeline...
            self.btn_r2map = QPushButton("Display Frequency-channel R² map")
            self.btn_timefreq = QPushButton("Display Time-Frequency ERD/ERS analysis")
            self.btn_psd = QPushButton("Display PSD comparison between classes")
            self.btn_topo = QPushButton("Display Brain Topography")
            titleR2 = "Freq.-chan. map of R² values of spectral power between classes"
            titleTimeFreq = "Time-Frequency ERD/ERS analysis"
            titlePsd = "Power Spectrum "
            titleTopo = "Topography of power spectra, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2))
            self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq(self.Features, titleTimeFreq))
            self.btn_psd.clicked.connect(lambda: self.btnPsd(self.Features, titlePsd))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))

            self.parallelVizLayouts[0].addWidget(self.btn_r2map)
            self.parallelVizLayouts[0].addWidget(self.btn_psd)
            self.parallelVizLayouts[0].addWidget(self.btn_timefreq)
            self.parallelVizLayouts[0].addWidget(self.btn_topo)

            self.layoutViz.addLayout(self.parallelVizLayouts[0])

        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # Viz options for "Connectivity" pipeline...
            self.btn_r2map = QPushButton("Display Frequency-channel R² map (NODE STRENGTH)")
            # self.btn_timefreq = QPushButton("Display Time-Frequency ERD/ERS analysis")
            self.btn_metric = QPushButton("Display NODE STRENGTH comparison between classes")
            self.btn_topo = QPushButton("Display NODE STRENGTH Brain Topography")
            titleR2 = "Freq.-chan. map of R² values of node strength"
            titleTimeFreq = "Time-Frequency ERD/ERS analysis"
            titleMetric = "Connectivity-based node strength, "
            titleTopo = "Topography of node strengths, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2))
            self.btn_metric.clicked.connect(lambda: self.btnMetric(self.Features, titleMetric))
            # self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq(self.Features, titleTimeFreq))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))
            self.parallelVizLayouts[1].addWidget(self.btn_r2map)
            self.parallelVizLayouts[1].addWidget(self.btn_metric)
            # self.parallelVizLayouts[1].addWidget(self.btn_timefreq)
            self.parallelVizLayouts[1].addWidget(self.btn_topo)

            self.layoutViz.addLayout(self.parallelVizLayouts[1])

        elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            # Viz options in parallel
            labelPowSpectViz = QLabel("Power Spectrum")
            labelPowSpectViz.setAlignment(QtCore.Qt.AlignCenter)
            labelConnectViz = QLabel("Node Strength")
            labelConnectViz.setAlignment(QtCore.Qt.AlignCenter)
            self.labelLayoutH = QHBoxLayout()
            self.labelLayoutH.addWidget(labelPowSpectViz)
            self.labelLayoutH.addWidget(labelConnectViz)

            # Viz options for "Spectral Power" pipeline...
            self.btn_r2map = QPushButton("Freq.-chan. R² map")
            self.btn_psd = QPushButton("PSD for the 2 classes")
            self.btn_topo = QPushButton("Brain Topography")
            titleR2 = "Freq.-chan. map of R² values of spectral power between classes"
            titleTimeFreq = "Time-Frequency ERD/ERS analysis"
            titlePsd = "Power Spectrum "
            titleTopo = "Topography of power spectra, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2))
            self.btn_psd.clicked.connect(lambda: self.btnPsd(self.Features, titlePsd))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))
            self.parallelVizLayouts[0].addWidget(self.btn_r2map)
            self.parallelVizLayouts[0].addWidget(self.btn_psd)
            self.parallelVizLayouts[0].addWidget(self.btn_topo)

            # Viz options for "Connectivity" pipeline...
            self.btn_r2map2 = QPushButton("Freq.-chan. R² map")
            self.btn_metric = QPushButton("NodeStr. for the 2 classes")
            self.btn_topo2 = QPushButton("Brain Topography")
            titleR2_c = "Freq.-chan. map of R² values of node strength"
            titleTimeFreq_c = "Time-Frequency ERD/ERS analysis"
            titleMetric_c = "Connectivity-based Node Strength, "
            titleTopo_c = "Topography of node strengths, for freq. "
            self.btn_r2map2.clicked.connect(lambda: self.btnR2(self.Features2, titleR2_c))
            self.btn_metric.clicked.connect(lambda: self.btnMetric(self.Features2, titleMetric_c))
            self.btn_topo2.clicked.connect(lambda: self.btnTopo(self.Features2, titleTopo_c))
            self.parallelVizLayouts[1].addWidget(self.btn_r2map2)
            self.parallelVizLayouts[1].addWidget(self.btn_metric)
            self.parallelVizLayouts[1].addWidget(self.btn_topo2)

            # Setting up parallel layouts...
            self.parallelVizLayoutH = QHBoxLayout()
            self.parallelVizLayoutH.addLayout(self.parallelVizLayouts[0])
            self.parallelVizLayoutH.addLayout(self.parallelVizLayouts[1])

            self.layoutViz.addLayout(self.labelLayoutH)
            self.layoutViz.addLayout(self.parallelVizLayoutH)

        # Add separator...
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        separator2.setLineWidth(1)

        # Add all this to the "general" Layout
        self.dlgLayout.addLayout(self.layoutViz, 1)
        self.dlgLayout.addWidget(separator2)

        # -----------------------------------------------------------------------
        # RIGHTMOST PART: FEATURE SELECTION + TRAINING
        # SELECT FEATURES OF INTEREST, AND FILE(S) TO USE FOR TRAINING
        # LAUNCH THE TRAINING SCENARIO/THREAD

        self.layoutTrain = QVBoxLayout()
        self.layoutTrain.setAlignment(QtCore.Qt.AlignTop)

        self.labelTrain = QLabel('== CLASSIFIER TRAINING ==')
        self.labelTrain.setAlignment(QtCore.Qt.AlignCenter)
        self.labelTrain.setFont(QFont("system-ui", 12))
        self.labelTrain.setStyleSheet("font-weight: bold")
        self.layoutTrain.addWidget(self.labelTrain)

        textFeatureSelect = "Ex:\tFCz;14"
        textFeatureSelect = str(textFeatureSelect + "\n\tFCz;14:22 (for freq range)")
        self.labelSelect = QLabel(textFeatureSelect)
        self.labelSelect.setAlignment(QtCore.Qt.AlignCenter)
        self.layoutTrain.addWidget(self.labelSelect)

        # Feature selection layouts. Usually only 1, but 2 parallel selections in "mixed" mode
        self.qvFeatureLayouts = [None, None]
        self.qvFeatureLayouts[0] = QFormLayout()
        self.qvFeatureLayouts[1] = QFormLayout()
        if self.parameterDict["pipelineType"] != settings.optionKeys[3]:
            self.layoutTrain.addLayout(self.qvFeatureLayouts[0])
        else:
            labelFeat = [None, None]
            labelFeat[0] = QLabel("Power Spectrum")
            labelFeat[0].setAlignment(QtCore.Qt.AlignCenter)
            labelFeat[0].setStyleSheet("font-weight: bold")
            labelFeat[1] = QLabel("Connectivity")
            labelFeat[1].setAlignment(QtCore.Qt.AlignCenter)
            labelFeat[1].setStyleSheet("font-weight: bold")
            self.qvFeatureLayouts[0].addWidget(labelFeat[0])
            self.qvFeatureLayouts[1].addWidget(labelFeat[1])
            qhBoxFeatLayout = QHBoxLayout()
            qhBoxFeatLayout.addLayout(self.qvFeatureLayouts[0], 1)
            qhBoxFeatLayout.addLayout(self.qvFeatureLayouts[1], 1)
            self.layoutTrain.addLayout(qhBoxFeatLayout)

        # Parameter for feat selection/training : First selected pair of Channels / Electrodes
        # We'll add more with a button
        pairText = "Feature 1"
        self.selectedFeats = [[], []]

        self.selectedFeats[0].append(QLineEdit())
        self.selectedFeats[0][0].setText('CP3;22')

        self.btn_addPair = QPushButton("Add feature")
        self.btn_removePair = QPushButton("Remove feature")
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair(self.selectedFeats[0], self.qvFeatureLayouts[0]))
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair(self.selectedFeats[0], self.qvFeatureLayouts[0]))
        self.qvFeatureLayouts[0].addWidget(self.btn_addPair)
        self.qvFeatureLayouts[0].addWidget(self.btn_removePair)
        self.qvFeatureLayouts[0].addWidget(self.selectedFeats[0][0])

        if self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            self.selectedFeats[1].append(QLineEdit())
            self.selectedFeats[1][0].setText('CP3;22')

            self.btn_addPair2 = QPushButton("Add feature")
            self.btn_removePair2 = QPushButton("Remove feature")
            self.btn_addPair2.clicked.connect(lambda: self.btnAddPair(self.selectedFeats[1], self.qvFeatureLayouts[1]))
            self.btn_removePair2.clicked.connect(lambda: self.btnRemovePair(self.selectedFeats[1], self.qvFeatureLayouts[1]))
            self.qvFeatureLayouts[1].addWidget(self.btn_addPair2)
            self.qvFeatureLayouts[1].addWidget(self.btn_removePair2)
            self.qvFeatureLayouts[1].addWidget(self.selectedFeats[1][0])

        # Training Layout
        self.qvTrainingLayout = QVBoxLayout()
        self.layoutTrain.addLayout(self.qvTrainingLayout)

        # Param for training
        self.trainingParamsLayout = QFormLayout()
        self.trainingPartitions = QLineEdit()
        self.trainingPartitions.setText(str(10))
        partitionsText = "Number of k-fold for classification"
        self.trainingParamsLayout.addRow(partitionsText, self.trainingPartitions)

        # List of files...
        self.fileListWidgetTrain = QListWidget()
        self.fileListWidgetTrain.setSelectionMode(QListWidget.MultiSelection)

        # Label + un-editable plain text for last results
        labelLastResults = str("--- Last Training Results ---")
        self.labelLastResults = QLabel(labelLastResults)
        self.labelLastResults.setAlignment(QtCore.Qt.AlignCenter)

        self.lastTrainingResults = QPlainTextEdit()
        self.lastTrainingResults.setReadOnly(True)
        self.lastTrainingResults.setStyleSheet("background-color: rgb(200,200,200)")
        minHeightTrainResults = 30
        self.lastTrainingResults.setMinimumHeight(minHeightTrainResults)
        self.lastTrainingResults.insertPlainText("No training attempts yet...")

        # Select / all combinations buttons...
        self.btn_selectFeatures = QPushButton("TRAIN CLASSIFIER")
        self.btn_allCombinations = QPushButton("FIND BEST COMBINATION")
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())
        self.btn_allCombinations.clicked.connect(lambda: self.btnAllCombinations())
        self.btn_selectFeatures.setStyleSheet("font-weight: bold")
        self.btn_allCombinations.setStyleSheet("font-weight: bold")

        # Connectivity: allow to enable/disable "Speed up" training"
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.enableSpeedUp = QCheckBox()
            self.enableSpeedUp.setTristate(False)
            self.enableSpeedUp.setChecked(False)
            speedUpLabel = str("Speed-up training (experimental)")
            self.speedUpLabel = QLabel(speedUpLabel)
            self.speedUpLabel.setAlignment(QtCore.Qt.AlignCenter)
            self.speedUpLayout = QHBoxLayout()
            self.speedUpLayout.addWidget(self.speedUpLabel)
            self.speedUpLayout.addWidget(self.enableSpeedUp)

        self.qvTrainingLayout.addLayout(self.trainingParamsLayout)
        self.qvTrainingLayout.addWidget(self.fileListWidgetTrain)
        self.qvTrainingLayout.addWidget(self.labelLastResults)
        self.qvTrainingLayout.addWidget(self.lastTrainingResults)
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.qvTrainingLayout.addLayout(self.speedUpLayout)
        self.qvTrainingLayout.addWidget(self.btn_selectFeatures)
        self.qvTrainingLayout.addWidget(self.btn_allCombinations)
        self.dlgLayout.addLayout(self.layoutTrain, 1)

        # display initial layout
        self.setLayout(self.dlgLayout)
        self.btn_loadFilesForViz.setEnabled(True)
        self.enablePlotBtns(False)

        self.refreshLists(os.path.join(self.scriptPath, "generated", "signals"))

        # Timing loop every 4s to get files in working folder
        self.filesRefreshTimer = QtCore.QTimer(self)
        self.filesRefreshTimer.setSingleShot(False)
        self.filesRefreshTimer.setInterval(4000)  # in milliseconds
        self.filesRefreshTimer.timeout.connect(lambda: self.refreshLists(os.path.join(self.scriptPath, "generated", "signals")))
        self.filesRefreshTimer.start()

    # -----------------------------------------------------------------------
    # CLASS METHODS
    # -----------------------------------------------------------------------
    def enablePlotBtns(self, myBool):
        # ----------
        # Update status of buttons used for plotting
        # ----------
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.btn_r2map.setEnabled(myBool)
            self.btn_timefreq.setEnabled(myBool)
            self.btn_psd.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # self.btn_connectSpect.setEnabled(myBool)
            # self.btn_connectMatrices.setEnabled(myBool)
            # self.btn_connectome.setEnabled(myBool)
            self.btn_r2map.setEnabled(myBool)
            self.btn_metric.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            self.btn_r2map.setEnabled(myBool)
            self.btn_psd.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
            self.btn_r2map2.setEnabled(myBool)
            self.btn_metric.setEnabled(myBool)
            self.btn_topo2.setEnabled(myBool)

        self.show()

    def refreshLists(self, workingFolder):
        # ----------
        # Refresh all lists. Called once at the init, then once every timer click (see init method)
        # ----------
        self.refreshSignalList(self.fileListWidget, workingFolder)
        self.refreshAvailableFilesForVizList(workingFolder)
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

    def refreshAvailableFilesForVizList(self, signalFolder):
        # ----------
        # Refresh available CSV spectrum files.
        # Only mention current class (set in parameters), and check that both classes are present
        # ----------

        suffix1 = None
        suffix2 = None
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            suffix1 = "-SPECTRUM"
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            suffix1 = "-CONNECT"
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            suffix1 = "-SPECTRUM"
            suffix2 = "-CONNECT"
        suffixFinal = suffix1
        if suffix2:
            suffixFinal += suffix2

        workingFolder = os.path.join(signalFolder, "analysis")
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]

        # first get a list of all csv files in workingfolder that match the condition
        availableCsvs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str(suffix1 + "-" + class1label + ".csv")):
                basename = filename.removesuffix(str(suffix1 + "-" + class1label + ".csv"))
                otherClass = str(basename + suffix1 + "-" + class2label + ".csv")
                if otherClass in os.listdir(workingFolder):
                    if not suffix2:
                        # no need to check for additional files...
                        availableCsvs.append(basename)
                    else:
                        # we need to check that files with suffix 2 are also present
                        otherMetric1 = str(basename + suffix2 + "-" + class1label + ".csv")
                        otherMetric2 = str(basename + suffix2 + "-" + class2label + ".csv")
                        if otherMetric1 in os.listdir(workingFolder) and otherMetric2 in os.listdir(workingFolder):
                            availableCsvs.append(basename)

        suffixFinal = suffix1
        if suffix2:
            suffixFinal += suffix2
        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.availableFilesForVizList.count() - 1, -1, -1):
            tempitem = self.availableFilesForVizList.item(x).text()
            if tempitem.removesuffix(suffixFinal) not in availableCsvs:
                self.availableFilesForVizList.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.availableFilesForVizList.count()):
            items.append(self.availableFilesForVizList.item(x).text())
        for basename in availableCsvs:
            basenameSuffix = str(basename+suffixFinal)
            if basenameSuffix not in items:
                self.availableFilesForVizList.addItem(basenameSuffix)

        return

    def refreshAvailableTrainSignalList(self, signalFolder):
        # ----------
        # Refresh available training files.
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
        # ----------
        # Get new extraction parameters
        # return True if params where changed from last known config
        # ----------
        changed = False

        # Retrieve param id from label...
        for idx in range(self.layoutExtractLabels.count()):
            paramLabel = self.layoutExtractLabels.itemAt(idx).widget().text()
            # special case : combobox for connectivity metric
            if paramLabel == "Connectivity Metric":
                paramValue = None
                for k, v in settings.connectMetricsComboText.items():
                    if v == self.layoutExtractLineEdits.itemAt(idx).widget().currentText():
                        paramValue = k
                paramId = list(settings.paramIdText.keys())[list(settings.paramIdText.values()).index(paramLabel)]
            else:
                paramValue = self.layoutExtractLineEdits.itemAt(idx).widget().text()
                paramId = list(settings.paramIdText.keys())[list(settings.paramIdText.values()).index(paramLabel)]

            if paramId in self.parameterDict:
                if self.parameterDict[paramId] != paramValue:
                    changed = True
                    self.parameterDict[paramId] = paramValue
            else:
                # first time the extraction parameters are written
                changed = True
                self.parameterDict[paramId] = paramValue

        if changed:
            # update json file
            with open(self.jsonfullpath, "w") as outfile:
                json.dump(self.parameterDict, outfile, indent=4)

        return changed

    def deleteWorkFiles(self):
        # ----------
        # Remove work files in folders "signals", "signals/analysis" and "signal/training"
        # ----------
        path1 = os.path.join(self.scriptPath, "generated", "signals", "analysis")
        path2 = os.path.join(self.scriptPath, "generated", "signals", "training")
        for file in os.listdir(path1):
            if file.endswith('.csv'):
                os.remove(os.path.join(path1, file))
        for file in os.listdir(path2):
            if file.endswith('.csv') or file.endswith('.xml'):
                os.remove(os.path.join(path2, file))
        return

    def runAcquisitionScenario(self):
        # ----------
        # Use acquisition scenario (sc1-monitor-acq.xml) to record
        # EEG signals and Stimulations, as .ov files, using the acquisition parameters
        # set in GUI 1
        # ----------

        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[0])

        # disable this part of the GUI...
        self.enableAcquisitionGui(False)

        # Instantiate the thread...
        self.acquisitionThread = Acquisition(self.ovScript, scenFile, self.parameterDict)
        # Signal: Extraction work thread finished
        self.acquisitionThread.over.connect(self.acquisition_over)
        # Launch the work thread
        self.acquisitionThread.start()
        return

    def acquisition_over(self, success, text):
        # Extraction work thread is over, display a msg if an error occurred
        if not success:
            myMsgBox(text)
        self.enableAcquisitionGui(True)

    def runExtractionScenario(self):
        # ----------
        # Use extraction scenario (sc2-extract-select.xml) to
        # generate CSV files from the OV signal (for visualization and trials
        # concatenation for training)
        # Before that, make sure the Metadata file associated to the OV signal file
        # exists, or generate it using toolbox-generate-metadata.xml
        # ----------

        # Check if files/sessions have been selected...
        if not self.fileListWidget.selectedItems():
            myMsgBox("Please select a set of files for feature extraction")
            return

        # Update extraction parameters, and delete work files if necessary
        if self.updateExtractParameters():
            self.deleteWorkFiles()

        # Populate list of selected signal files...
        signalFiles = []
        for selectedItem in self.fileListWidget.selectedItems():
            signalFiles.append(selectedItem.text() )
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[1])

        # create progress bar window...
        self.progressBarExtract = ProgressBar("Feature extraction",
                                              str("Extracting data for file "+signalFiles[0]+"..."),
                                              len(self.fileListWidget.selectedItems()))

        # deactivate this part of the GUI
        self.enableExtractionGui(False)

        # deactivate automatic file refresh, or else we might get .csv files in
        # the viz and train lists before they're ready to be used
        self.filesRefreshTimer.stop()

        # Instantiate the thread...
        self.extractThread = Extraction(self.ovScript, scenFile, signalFiles, signalFolder, self.parameterDict)
        # Signal: Extraction work thread finished one file of the selected list.
        # Refresh the viz&train file lists to make it available + increment progress bar
        self.extractThread.info.connect(self.progressBarExtract.increment)
        self.extractThread.info.connect(lambda : self.refreshLists(os.path.join(self.scriptPath, "generated", "signals")))
        self.extractThread.info2.connect(self.progressBarExtract.changeLabel)
        # Signal: Extraction work thread finished
        self.extractThread.over.connect(self.extraction_over)
        # Launch the work thread
        self.extractTimerStart = time.perf_counter()
        self.extractThread.start()

    def extraction_over(self, success, text):
        # Extraction work thread is over, so we kill the progress bar,
        # display a msg if an error occurred, restart the timer and
        # make the extraction Gui available again
        self.extractTimerEnd = time.perf_counter()

        elapsed = self.extractTimerEnd-self.extractTimerStart
        print("=== Extraction finished in: ", str(elapsed))

        self.progressBarExtract.finish()
        if not success:
            myMsgBox(text)
        self.filesRefreshTimer.start()
        self.enableExtractionGui(True)

    def loadFilesForViz(self):
        # ----------
        # Load CSV files of selected extracted files for visualization
        # We need one CSV file per class, for simplicity...
        # ----------
        if not self.availableFilesForVizList.selectedItems():
            myMsgBox("Please select a set of files for analysis")
            return

        suffix = ""
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
           suffix = "-SPECTRUM"
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            suffix = "-CONNECT"
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            suffix = "-SPECTRUM-CONNECT"

        analysisFiles = []
        for selectedItem in self.availableFilesForVizList.selectedItems():
            analysisFiles.append(selectedItem.text().removesuffix(suffix))
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")

        # deactivate this part of the GUI + the extraction (or else we might have sync issues)
        self.enableExtractionGui(False)
        self.enableVizGui(False)

        # Instantiate the thread...
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, signalFolder, self.parameterDict, self.Features, self.samplingFreq)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.loadFilesForVizThread = LoadFilesForVizConnectivity(analysisFiles, signalFolder, self.parameterDict, self.Features, self.samplingFreq)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, signalFolder, self.parameterDict, self.Features, self.samplingFreq)
            self.loadFilesForVizThread2 = LoadFilesForVizConnectivity(analysisFiles, signalFolder, self.parameterDict, self.Features2, self.samplingFreq)

        # create progress bar window...
        self.progressBarViz = ProgressBar("Feature Visualization", "Loading data from Csv files...",
                                          len(self.availableFilesForVizList.selectedItems()))
        # Signal: Viz work thread finished one file of the selected list.
        # Increment progress bar + its label
        self.loadFilesForVizThread.info.connect(self.progressBarViz.increment)
        self.loadFilesForVizThread.info2.connect(self.progressBarViz.changeLabel)
        # Signal: Viz work thread finished
        self.loadFilesForVizThread.over.connect(self.loadFilesForViz_over)
        # Launch the work thread
        self.loadFilesForVizThread.start()

        if self.loadFilesForVizThread2:
            # create progress bar window...
            self.progressBarViz2 = ProgressBar("Feature Visualization", "Loading data from Csv files...",
                                              len(self.availableFilesForVizList.selectedItems()))
            # Signal: Viz work thread finished one file of the selected list.
            # Increment progress bar + its label
            self.loadFilesForVizThread2.info.connect(self.progressBarViz2.increment)
            self.loadFilesForVizThread2.info2.connect(self.progressBarViz2.changeLabel)
            # Signal: Viz work thread finished
            self.loadFilesForVizThread2.over.connect(self.loadFilesForViz_kill_PB)
            # Launch the work thread
            self.loadFilesForVizThread2.start()

        self.vizTimerStart = time.perf_counter()

    def loadFilesForViz_over(self, success, text):
        # Viz work thread is over, so we kill the progress bar,
        # and make the viz Gui available again
        self.vizTimerEnd = time.perf_counter()
        elapsed = self.vizTimerEnd - self.vizTimerStart
        print("=== Viz data loaded in: ", str(elapsed))

        self.progressBarViz.finish()
        if not success:
            myMsgBox(text)
            self.plotBtnsEnabled = False
        else:
            self.samplingFreq = self.Features.samplingFreq
            self.plotBtnsEnabled = True
        self.enableGui(True)

    def loadFilesForViz_kill_PB(self, success, text):
        # Viz work thread2 is over, so we only kill the progress bar
        self.progressBarViz2.finish()

    def btnSelectFeatures(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------
        if not self.fileListWidgetTrain.selectedItems():
            myMsgBox("Please select a set of files for training")
            return

        if not self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            # case with 1 set of features...
            if len(self.selectedFeats[0]) < 1:
                myMsgBox("Please use at least one set of features!")
                return
        else:
            # case with 2 sets of features : one of the two can be empty
            if len(self.selectedFeats[0]) < 1 and len(self.selectedFeats[1]) < 1:
                myMsgBox("Please use at least one set of features!")
                return

        # Get training param from GUI and modify training scenario
        err = True
        trainingSize = 0
        if self.trainingPartitions.text().isdigit():
            if int(self.trainingPartitions.text()) > 0:
                trainingSize = int(self.trainingPartitions.text())
                err = False
        if err:
            myMsgBox("Nb of k-fold should be a positive number")
            return

        # create list of files...
        self.trainingFiles = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            self.trainingFiles.append(selectedItem.text())

        # IMPORTANT !
        # When using "mixed" pipeline, if one of the two feature lists is empty, we use
        # the Training scenario template from the pipeline with the non-empty feature (got it?)
        # ex: if feats(connectivity) is empty, then we use the "powerspectrum" template.
        trainingParamDict = self.parameterDict.copy()
        trainingFeats = self.selectedFeats
        if self.parameterDict["pipelineType"] != settings.optionKeys[3]:
            trainingFeats = self.selectedFeats[0]
        else:
            trainingFeats = self.selectedFeats
            if len(self.selectedFeats[0]) < 1:
                # no powspectum feature = use connectivity pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[2]
                # copy the selected feats to the first list, for processing in the thread...
                trainingFeats = self.selectedFeats[1]
            elif len(self.selectedFeats[1]) < 1:
                # no connectivity feature = use powspectrum pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[1]
                trainingFeats = self.selectedFeats[0]

        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        pipelineType = trainingParamDict["pipelineType"]
        templateFolder = os.path.join(self.scriptPath, settings.optionsTemplatesDir[pipelineType])
        scriptsFolder = self.scriptPath

        # deactivate this part of the GUI (+ the extraction part)
        self.enableExtractionGui(False)
        self.enableTrainGui(False)

        # create progress bar window...
        self.progressBarTrain = ProgressBar("Classifier training", "Creating composite file", 2)

        # Instantiate the thread...
        combiComp = False
        enableSpeedUp = False
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            if self.enableSpeedUp.isChecked():
                enableSpeedUp = True

        self.trainClassThread = TrainClassifier(combiComp, self.trainingFiles,
                                                signalFolder, templateFolder, scriptsFolder, self.ovScript,
                                                trainingSize, trainingFeats,
                                                trainingParamDict, self.samplingFreq, enableSpeedUp)

        # Signal: Training work thread finished one step
        # Increment progress bar + change its label
        self.trainClassThread.info.connect(self.progressBarTrain.increment)
        self.trainClassThread.info2.connect(self.progressBarTrain.changeLabel)
        # Signal: Training work thread finished
        self.trainClassThread.over.connect(self.training_over)
        # Launch the work thread
        self.trainClassThread.start()

        self.trainTimerStart = time.perf_counter()

    def btnAllCombinations(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------
        if not self.fileListWidgetTrain.selectedItems():
            myMsgBox("Please select a set of runs for training")
            return
        elif len(self.fileListWidgetTrain.selectedItems()) > 5:
            myMsgBox("Please select 5 runs maximum")
            return

        if not self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            # case with 1 set of features...
            if len(self.selectedFeats[0]) < 1:
                myMsgBox("Please use at least one set of features!")
                return
        else:
            # case with 2 sets of features : one of the two can be empty
            if len(self.selectedFeats[0]) < 1 and len(self.selectedFeats[1]) < 1:
                myMsgBox("Please use at least one set of features!")
                return

        # Get training param from GUI and modify training scenario
        err = True
        trainingSize = 0
        if self.trainingPartitions.text().isdigit():
            if int(self.trainingPartitions.text()) > 0:
                trainingSize = int(self.trainingPartitions.text())
                err = False
        if err:
            myMsgBox("Nb of k-fold should be a positive number")
            return

        # create list of files...
        self.trainingFiles = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            self.trainingFiles.append(selectedItem.text())
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        pipelineType = self.parameterDict["pipelineType"]
        templateFolder = os.path.join(self.scriptPath, settings.optionsTemplatesDir[pipelineType])
        scriptsFolder = self.scriptPath

        # IMPORTANT !
        # When using "mixed" pipeline, if one of the two feature lists is empty, we use
        # the Training scenario template from the pipeline with the non-empty feature (got it?)
        # ex: if feats(connectivity) is empty, then we use the "powerspectrum" template.
        trainingParamDict = self.parameterDict.copy()
        trainingFeats = self.selectedFeats
        if self.parameterDict["pipelineType"] == settings.optionKeys[3]:
            trainingFeats = self.selectedFeats
            if len(self.selectedFeats[0]) < 1:
                # no powspectum feature = use connectivity pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[2]
                # copy the selected feats to the first list, for processing in the thread...
                trainingFeats[0] = self.selectedFeats[1]
            elif len(self.selectedFeats[1]) < 1:
                # no connectivity feature = use powspectrum pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[1]

        # deactivate this part of the GUI + the extraction part
        self.enableExtractionGui(False)
        self.enableTrainGui(False)

        # create progress bar window...
        i = []
        for item in self.fileListWidgetTrain.selectedItems():
            i.append("a")
        nbCombinations = len(list(myPowerset(i)))
        self.progressBarTrain = ProgressBar("Classifier Training", "First combination", nbCombinations)

        # Instantiate the thread...
        combiComp = True
        speedUp = False
        self.trainClassThread = TrainClassifier(combiComp, self.trainingFiles,
                                                signalFolder, templateFolder, scriptsFolder, self.ovScript,
                                                trainingSize, trainingFeats,
                                                trainingParamDict, self.samplingFreq, speedUp)
        # Signal: Extraction work thread finished one file of the selected list.
        # Refresh the viz&train file lists to make it available + increment progress bar
        self.trainClassThread.info.connect(self.progressBarTrain.increment)
        self.trainClassThread.info2.connect(self.progressBarTrain.changeLabel)
        # Signal: Extraction work thread finished
        self.trainClassThread.over.connect(self.training_over)
        # Launch the work thread
        self.trainClassThread.start()

        self.trainTimerStart = time.perf_counter()

    def training_over(self, success, resultsText):
        # Training work thread is over, so we kill the progress bar,
        # display a msg with results, and make the training Gui available again
        self.trainTimerEnd = time.perf_counter()
        elapsed = self.trainTimerEnd - self.trainTimerStart
        print("=== Training done in: ", str(elapsed))

        self.progressBarTrain.finish()
        if success:
            textGoodbye = str("Classifier weights were written in:\n\tgenerated/classifier-weights.xml\n")
            textGoodbye += str("If those results are satisfying, you can now open in the OV Designer:"
                               + "\n\tgenerated/sc3-online.xml in the Designer")

            textDisplayed = str(resultsText + "\n\n" + textGoodbye)
            msg = QMessageBox()
            msg.setText(textDisplayed)
            msg.setStyleSheet("QLabel{min-width: 1200px;}")
            msg.setWindowTitle("Classifier Training Score")
            msg.exec_()
            self.lastTrainingResults.clear()
            self.lastTrainingResults.appendPlainText(resultsText)
        else:
            myMsgBox(resultsText)
        self.enableGui(True)

    def enableAcquisitionGui(self, myBool):
        # Acquisition part...
        for idx in range(self.layoutAcqOnline.count()):
            self.layoutAcqOnline.itemAt(idx).widget().setEnabled(myBool)
        # self.btn_browseOvScript.setEnabled(myBool)
        self.menuOptions.setEnabled(myBool)

    def enableExtractionGui(self, myBool):
        # Extraction part...
        for idx in range(self.layoutExtractLabels.count()):
            self.layoutExtractLineEdits.itemAt(idx).widget().setEnabled(myBool)
        self.btn_runExtractionScenario.setEnabled(myBool)
        self.fileListWidget.setEnabled(myBool)
        # self.btn_browseOvScript.setEnabled(myBool)
        self.menuOptions.setEnabled(myBool)

    def enableVizGui(self, myBool):
        # Viz part...
        self.btn_loadFilesForViz.setEnabled(myBool)
        self.availableFilesForVizList.setEnabled(myBool)

        self.userFmin.setEnabled(myBool)
        self.userFmax.setEnabled(myBool)
        self.electrodePsd.setEnabled(myBool)
        self.freqTopo.setEnabled(myBool)
        self.colormapScale.setEnabled(myBool)

        self.btn_loadFilesForViz.setEnabled(myBool)
        if myBool and self.plotBtnsEnabled:
            self.enablePlotBtns(True)
        if not myBool:
            self.enablePlotBtns(False)

    def enableTrainGui(self, myBool):
        # Training part...
        self.btn_addPair.setEnabled(myBool)
        self.btn_removePair.setEnabled(myBool)
        self.btn_selectFeatures.setEnabled(myBool)
        self.btn_allCombinations.setEnabled(myBool)
        for listOfFeatures in self.selectedFeats:
            for item in listOfFeatures:
                item.setEnabled(myBool)
        self.trainingPartitions.setEnabled(myBool)
        self.fileListWidgetTrain.setEnabled(myBool)
        self.menuOptions.setEnabled(myBool)
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.enableSpeedUp.setEnabled(myBool)


    def enableGui(self, myBool):
        # Enable/Disable ALL PARTS of the GUI
        self.enableAcquisitionGui(myBool)
        self.enableExtractionGui(myBool)
        self.enableVizGui(myBool)
        self.enableTrainGui(myBool)

    def getExperimentalParameters(self):
        # ----------
        # Get experimental parameters from the JSON parameters
        # ----------
        newDict = settings.pipelineAcqSettings.copy()
        print(newDict)
        return newDict

    def getExtractionParameters(self):
        # ----------
        # Get "extraction" parameters from the JSON parameters
        # A bit artisanal, but we'll see if we keep that...
        # ----------
        pipelineKey = self.parameterDict['pipelineType']
        newDict = settings.pipelineExtractSettings[pipelineKey].copy()
        print(newDict)
        return newDict

    def btnR2(self, features, title):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(features.Rsigned,
                       features.freqs_array,
                       features.electrodes_final,
                       features.fres, int(self.userFmin.text()), int(self.userFmax.text()),
                       self.colormapScale.isChecked(), title)

    def btnW2(self, features, title):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(features.Wsigned,
                       features.freqs_array,
                       features.electrodes_final,
                       features.fres, int(self.userFmin.text()), int(self.userFmax.text()),
                       self.colormapScale.isChecked(), title)

    def btnTimeFreq(self, features, title):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            print("TimeFreq for sensor: " + self.electrodePsd.text())

            tmin = float(self.parameterDict['StimulationDelay'])
            tmax = float(self.parameterDict['StimulationEpoch'])
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]

            qt_plot_tf(features.timefreq_cond1, features.timefreq_cond2,
                       features.time_array, features.freqs_array,
                       self.electrodePsd.text(), features.fres,
                       features.average_baseline_cond1, features.average_baseline_cond2,
                       features.std_baseline_cond1, features.std_baseline_cond2,
                       features.electrodes_final,
                       fmin, fmax, tmin, tmax, class1, class2, title)

    def btnMetric(self, features, title):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]
            # TODO : change
            metricLabel = "Average Node Strength"
            #qt_plot_metric(features.power_cond1, features.power_cond2,
            #               features.freqs_array, features.electrodes_final,
            #               self.electrodePsd.text(),
            #               features.fres, fmin, fmax, class1, class2, metricLabel)
            qt_plot_metric2(features.power_cond1, features.power_cond2,
                            features.Rsigned,
                            features.freqs_array, features.electrodes_final,
                            self.electrodePsd.text(),
                            features.fres, fmin, fmax, class1, class2, metricLabel, title)

    def btnPsd(self, features, title):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]
            # qt_plot_psd(features.power_cond1, features.power_cond2,
            #            features.freqs_array, features.electrodes_final,
            #            self.electrodePsd.text(),
            #            features.fres, fmin, fmax, class1, class2)
            qt_plot_psd_r2(features.power_cond1, features.power_cond2,
                           features.Rsigned,
                            features.freqs_array, features.electrodes_final,
                            self.electrodePsd.text(),
                            features.fres, fmin, fmax, class1, class2, title)

    def btnTopo(self, features, title):
        error = True

        # First manage montage option...
        if self.sensorMontage == "custom":
            # TODO : get custom montage...
            myMsgBox("wow this is impossible as of today, please choose a standard montage in GUI 1")
            return

        # 2 cases : 1 freq bin, or freq range
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.samplingFreq / 2):
            print("Freq Topo: " + self.freqTopo.text())
            error = False
            freqMax = -1
            qt_plot_topo(features.Rsigned, self.sensorMontage, self.customMontagePath, features.electrodes_final,
                         int(self.freqTopo.text()), freqMax, features.fres, self.samplingFreq,
                         self.colormapScale.isChecked(), title)
        elif ":" in self.freqTopo.text() \
                and len(self.freqTopo.text().split(":")) == 2:
                    if self.freqTopo.text().split(":")[0].isdigit() \
                            and self.freqTopo.text().split(":")[1].isdigit():
                        freqMin = int(self.freqTopo.text().split(":")[0])
                        freqMax = int(self.freqTopo.text().split(":")[1])
                        if 0 < freqMin < freqMax < (self.samplingFreq / 2):
                            error = False
                            qt_plot_topo(features.Rsigned, self.sensorMontage, self.customMontagePath, features.electrodes_final,
                                         freqMin, freqMax, features.fres, self.samplingFreq,
                                         self.colormapScale.isChecked(), title)

        if error:
            myMsgBox("Invalid frequency for topography")

    def btnConnectSpect(self, features, title):
        qt_plot_connectSpectrum(features.connect_cond1, features.connect_cond2,
                                self.userChan1.text(), self.userChan2.text(), features.electrodes_orig,
                                features.fres, self.parameterDict["Class1"], self.parameterDict["Class2"], title)

    def btnConnectMatrices(self, features, title):
        if self.userFmin.text().isdigit() \
                and 0 < int(self.userFmin.text()) < (self.samplingFreq / 2) \
                and self.userFmax.text().isdigit() \
                and 0 < int(self.userFmax.text()) < (self.samplingFreq / 2):
            print("Freq connectivity matrices: " + self.userFmin.text() + " to " + self.userFmax.text())
        else:
            myMsgBox("Error in frequency used for displaying connectivity matrices...")
            return

        qt_plot_connectMatrices(features.connect_cond1, features.connect_cond2,
                                int(self.userFmin.text()), int(self.userFmax.text()),
                                features.electrodes_orig,
                                self.parameterDict["Class1"], self.parameterDict["Class2"], title)

    def btnConnectome(self, features, title):
        if self.percentStrong.text().isdigit() \
                and 0 < int(self.percentStrong.text()) <= 100:
            print("Percentage of strongest links: " + self.percentStrong.text() + "%")
        else:
            myMsgBox("Error in percentage used for displaying strongest links...")
            return

        if self.userFmin.text().isdigit() \
                and 0 < int(self.userFmin.text()) < (self.samplingFreq / 2) \
                and self.userFmax.text().isdigit() \
                and 0 < int(self.userFmax.text()) < (self.samplingFreq / 2):
            print("Freq connectivity matrices: " + self.userFmin.text() + " to " + self.userFmax.text())
        else:
            myMsgBox("Error in frequency used for displaying connectivity matrices...")
            return

        qt_plot_strongestConnectome(features.connect_cond1, features.connect_cond2,
                                    int(self.percentStrong.text()),
                                    int(self.userFmin.text()), int(self.userFmax.text()),
                                    features.electrodes_orig,
                                    self.parameterDict["Class1"], self.parameterDict["Class2"], title)

    def btnAddPair(self, selectedFeats, layout):
        if len(selectedFeats) == 0:
            # Remove "no feature" label
            item = layout.itemAt(3)
            widget = item.widget()
            widget.deleteLater()
        # default text
        featText = "CP3;22"
        if len(selectedFeats) >= 1:
            # if a feature window already exists, copy its text
            featText = selectedFeats[-1].text()
        # add new qlineedit
        selectedFeats.append(QLineEdit())
        selectedFeats[-1].setText(featText)
        layout.addWidget(selectedFeats[-1])

    def btnRemovePair(self, selectedFeats, layout):
        if len(selectedFeats) > 0:
            result = layout.getWidgetPosition(selectedFeats[-1])
            layout.removeRow(result[0])
            selectedFeats.pop()
            if len(selectedFeats) == 0:
                noFeatLabel = QLabel("No feature")
                noFeatLabel.setAlignment(QtCore.Qt.AlignCenter)
                layout.addWidget(noFeatLabel)

    def browseForDesigner(self):
        # ----------
        # Allow user to browse for the "openvibe-designer.cmd" windows cmd
        # ----------
        directory = os.getcwd()
        newPath, dummy = QFileDialog.getOpenFileName(self, "OpenViBE designer", str(directory))
        if "openvibe-designer.cmd" or "openvibe-designer.exe" or "openvibe-designer.sh" in newPath:
            # self.designerTextBox.setText(newPath)
            self.parameterDict["ovDesignerPath"] = newPath
            self.ovScript = newPath

        # TODO : add some check, to verify that it's an OpenViBE exec..? how..?
        #

        # TODO : update json file
        # ...
        return

    def updateJsonFile(self):
        with open(self.jsonfullpath, "w") as outfile:
            json.dump(self.parameterDict, outfile, indent=4)

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
        myMsgBox(errorStr)

    return ok

def plot_stats(Rsigned, freqs_array, electrodes, fres, fmin, fmax, colormapScale, title):
    smoothing = False
    plot_Rsquare_calcul_welch(Rsigned, np.array(electrodes)[:], freqs_array, smoothing, fres, 10, fmin, fmax, colormapScale, title)
    plt.show()

def qt_plot_psd(power_cond1, power_cond2, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label, title):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        myMsgBox("No sensor with this name found")
    else:
        plot_psd(power_cond1, power_cond2, freqs_array, electrodeIdx, electrodesList,
                 10, fmin, fmax, fres, class1label, class2label, title)
        plt.show()

def qt_plot_psd_r2(power_cond1, power_cond2, rsquare, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label, title):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        myMsgBox("No sensor with this name found")
    else:
        plot_psd_r2(power_cond1, power_cond2, rsquare, freqs_array, electrodeIdx, electrodesList,
                 10, fmin, fmax, fres, class1label, class2label, title)
        plt.show()

def qt_plot_metric(power_cond1, power_cond2, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label, metricLabel, title):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        myMsgBox("No sensor with this name found")
    else:
        plot_metric(power_cond1, power_cond2, freqs_array, electrodeIdx, electrodesList,
                    10, fmin, fmax, fres, class1label, class2label, metricLabel, title)
        plt.show()

def qt_plot_metric2(power_cond1, power_cond2, rsquare, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label, metricLabel, title):
    electrodeExists = False
    electrodeIdx = 0
    for idx, elec in enumerate(electrodesList):
        if elec == electrodeToDisp:
            electrodeIdx = idx
            electrodeExists = True
            break

    if not electrodeExists:
        myMsgBox("No sensor with this name found")
    else:
        plot_metric2(power_cond1, power_cond2, rsquare, freqs_array, electrodeIdx, electrodesList,
                    10, fmin, fmax, fres, class1label, class2label, metricLabel, title)
        plt.show()

# Plot "Brain topography", using either Power Spectrum (in same pipeline)
# or Node Strength (or similar metric) (in Connectivity pipeline)
def qt_plot_topo(Rsigned, montage, customMontage, electrodes, freqMin, freqMax, fres, fs, scaleColormap, title):
    topo_plot(Rsigned, title, montage, customMontage, electrodes, round(freqMin/fres), round(freqMax/fres),
              fres, fs, scaleColormap, 'Signed R square')
    plt.show()

# Plot "time-frequency analysis", in the POWER SPECTRUM pipeline ONLY.
def qt_plot_tf(timefreq_cond1, timefreq_cond2, time_array, freqs_array, electrode, fres, average_baseline_cond1, average_baseline_cond2, std_baseline_cond1, std_baseline_cond2, electrodes, f_min_var, f_max_var, tmin, tmax, class1label, class2label, title):
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
        myMsgBox("No Electrode with this name found")
    else:
        tf = timefreq_cond1.mean(axis=0)
        tf = np.transpose(tf[Index_electrode, :, :])
        PSD_baseline = average_baseline_cond1[Index_electrode, :]

        A = []
        for i in range(tf.shape[1]):
            A.append(np.divide((tf[:, i]-PSD_baseline), PSD_baseline)*100)
        tf = np.transpose(A)
        vmin = np.amin(tf[f_min_var:f_max_var, :])
        vmax = np.amax(tf[f_min_var:f_max_var, :])
        tlength = tmax-tmin
        time_frequency_map(timefreq_cond1, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10, average_baseline_cond1, electrodes, std_baseline_cond1, vmin, vmax, tlength)
        plt.title(title+'(' + class1label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
        time_frequency_map(timefreq_cond2, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10, average_baseline_cond2, electrodes, std_baseline_cond2, vmin, vmax, tlength)
        plt.title(title+'(' + class2label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
        plt.show()

# Plot "connectivity spectrum" from a RAW connectivity matrix. UNUSED
def qt_plot_connectSpectrum(connect1, connect2, chan1, chan2, electrodeList, fres, class1label, class2label, title):
    chan1ok = False
    chan2ok = False
    chan1idx = 0
    chan2idx = 0
    for idx, elec in enumerate(electrodeList):
        if elec == chan1:
            chan1idx = idx
            chan1ok = True
            if chan2ok:
                break
            else:
                continue
        elif elec == chan2:
            chan2idx = idx
            chan2ok = True
            if chan1ok:
                break
            else:
                continue

    if not chan1ok:
        myMsgBox("No sensor with name in Chan 1 found")
    if not chan2ok:
        myMsgBox("No sensor with name in Chan 2 found")
    else:
        plot_connect_spectrum(connect1, connect2, chan1idx, chan2idx, electrodeList, 10, fres, class1label, class2label, title)
        plt.show()

# Plot full RAW connectivity matrix for a given [fmin;fmax] range. UNUSED
def qt_plot_connectMatrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label, title):
    plot_connect_matrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label, title)
    plt.show()

# Plot % of strongest nodes, from a RAW connectivity matrix, in range [fmin;fmax]. UNUSED
def qt_plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label, title):
    plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label, title)
    plt.show()


def myMsgBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.exec_()
    return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())
