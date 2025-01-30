import sys
import os
import time
import subprocess
import platform
import json
import numpy as np
import matplotlib.pyplot as plt
import threading

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import QTreeWidget
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QMenuBar
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QAbstractItemView

from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer

from happyfeat.lib.Visualization_Data import *
from happyfeat.lib.featureExtractUtils import *
from happyfeat.lib.modifyOpenvibeScen import *
from happyfeat.lib.utils import *
from happyfeat.lib.workspaceMgmt import *
from happyfeat.lib.workThreads import *
from happyfeat.lib.myProgressBar import ProgressBar, ProgressBarNoInfo
from happyfeat.timeflux.Threads import *
import happyfeat.lib.bcipipeline_settings as settings

import plotly

class Features:
    Rsquare = []
    Rsign_tab = []
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

    autoselected = []

class Dialog(QDialog):

    def __init__(self, workspaceFile, parent=None):

        super().__init__(parent)

        self.workspaceFile = workspaceFile
        self.workspaceFolder = os.path.splitext(workspaceFile)[0]

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
        self.currentSessionId = None
        self.currentAttempt = []
        self.currentTrainCombination = None

        self.nbThreadsViz = 1
        self.vizThreadStatus = []

        self.extractTimerStart = 0
        self.extractTimerEnd = 0
        self.vizTimerStart = 0
        self.vizTimerEnd = 0
        self.trainTimerStart = 0
        self.trainTimerEnd = 0

        # Extraction stimulations
        self.extractionStims = "OVTK_GDF_Left;OVTK_GDF_Right"  # default values

        # Fmin and Fmax for R2map and comparison plots: default values
        # (can be set by top menu options)
        self.userFmin = 0
        self.userFmax = 40

        # default parameters for automatic selection
        self.autoFeatChannelList = []
        self.autoFeatFreqRange = ""

        # Work Threads & Progress bars
        self.acquisitionThread = None
        self.extractThread = None
        self.loadFilesForVizThread = None
        self.loadFilesForVizThread2 = None
        self.lockVizGui = threading.Lock()
        self.trainClassThread = []
        self.progressBarExtract = None
        self.progressBarViz = None
        self.progressBarViz2 = None
        self.progressBarTrain = None

        # "Advanced mode" with more options...?
        self.advanced = False

        self.useR2SignDict = {0:"No", 1:"Class2>Class1", 2:"Class1>Class2"}

        # GET BASIC SETTINGS FROM WORKSPACE FILE
        if self.workspaceFile:
            print("--- Using parameters from workspace file: " + workspaceFile)
            with open(self.workspaceFile) as jsonfile:
                self.parameterDict = json.load(jsonfile)
            self.bciPlatform = self.parameterDict["bciPlatform"]
            self.sensorMontage = self.parameterDict["sensorMontage"]
            self.customMontagePath = self.parameterDict["customMontagePath"]
            self.currentSessionId = self.parameterDict["currentSessionId"]
            self.extractionStims = self.parameterDict["extractionStims"]
            self.autoFeatFreqRange = self.parameterDict["autoFeatFreqRange"]
            self.autoFeatChannelList = self.parameterDict["autoFeatChannelList"]
            if self.bciPlatform == settings.availablePlatforms[0]:  # openvibe
                self.ovScript = self.parameterDict["ovDesignerPath"]
            else:
                self.ovScript = ""

        # -----------------------------------------------------------------------
        # CREATE INTERFACE...
        # dlgLayout : Entire Window, separated in horizontal panels
        # Left-most: layoutExtract (for running sc2-extract)
        # Center: Visualization
        # Right-most: Feature Selection & classifier training
        self.setWindowTitle('HappyFeat - Feature Selection interface')
        self.dlgLayout = QHBoxLayout()

        ## Create top bar menus...

        # menu "Options"
        self.menuBar = QMenuBar(self)
        self.dlgLayout.setMenuBar(self.menuBar)
        self.menuOptions = QMenu("&Options")
        self.menuBar.addMenu(self.menuOptions)

        # Options / OpenViBE designer browser
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            self.qActionFindOV = QAction("&Browse for OpenViBE", self)
            self.qActionFindOV.triggered.connect(lambda: self.browseForDesigner())
            self.menuOptions.addAction(self.qActionFindOV)
        # Options / Activate/deactivate advanced mode
        self.qActionEnableAdvancedMode = QAction("&Enable/Disable Advanced Mode", self)
        self.qActionEnableAdvancedMode.triggered.connect(lambda: self.toggleAdvanced())
        self.menuOptions.addAction(self.qActionEnableAdvancedMode)

        # Menu "Extraction"
        self.menuExtraction = QMenu("&Extraction")
        self.menuBar.addMenu(self.menuExtraction)

        self.qActionStimulations = QAction("Set Class &Stimulations", self)
        self.qActionStimulations.triggered.connect(lambda: self.extractionSetStimulations())
        self.menuExtraction.addAction(self.qActionStimulations)

        # Menu "Visualization"
        self.menuVizualization = QMenu("&Visualization")
        self.menuBar.addMenu(self.menuVizualization)

        self.qActionFreqMin = QAction("Set min frequency for R2 map and metric plot", self)
        self.qActionFreqMin.triggered.connect(lambda: self.vizSetFreqMin())
        self.menuVizualization.addAction(self.qActionFreqMin)
        self.qActionFreqMax = QAction("Set max frequency for R2 map and metric plot", self)
        self.qActionFreqMax.triggered.connect(lambda: self.vizSetFreqMax())
        self.menuVizualization.addAction(self.qActionFreqMax)

        # Menu "Auto-select"
        self.menuAutoSelect = QMenu("&Feature AutoSelect")
        self.menuBar.addMenu(self.menuAutoSelect)

        self.qActionChanList = QAction("Set &Channel sub-selection", self)
        self.qActionChanList.triggered.connect(lambda: self.autoFeatSetChannelSubselection())
        self.menuAutoSelect.addAction(self.qActionChanList)

        self.qActionFreqRange = QAction("Set frequency &Range", self)
        self.qActionFreqRange.triggered.connect(lambda: self.autoFeatSetFreqRange())
        self.menuAutoSelect.addAction(self.qActionFreqRange)

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

        # Copy extraction parameters from workspace file.
        # create a new dict (extractParamsDict) with defaults params...
        self.extractParamsDict = self.getDefaultExtractionParameters()
        # ... then copy from existing params file

        # special case: if current session id does not exist, load the "last" one
        if not self.parameterDict["Sessions"][self.currentSessionId]:
            for sessionId in self.parameterDict["Sessions"].keys():
                self.currentSessionId = sessionId

        for (key, elem) in enumerate(self.extractParamsDict):
            if elem in self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"]:
                self.extractParamsDict[elem] = self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"][elem]

        # Create layouts...
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
                lineEditExtractTemp.setText(str(self.extractParamsDict[paramId]))
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

        # Update button
        self.btn_updateExtractParams = QPushButton("Update with current extraction params")
        self.btn_updateExtractParams.clicked.connect(lambda: self.updateExtractParameters())

        # Extraction button
        self.btn_runExtractionScenario = QPushButton("Extract Features and Trials")
        self.btn_runExtractionScenario.clicked.connect(lambda: self.runExtractionScenario())
        self.btn_runExtractionScenario.setStyleSheet("font-weight: bold")

        # Arrange all widgets in the layout
        self.layoutExtract.addWidget(self.labelFeatExtract)
        self.layoutExtract.addWidget(self.fileListWidget)
        self.layoutExtract.addWidget(self.labelExtractParams)
        self.layoutExtract.addLayout(extractParametersLayout)
        self.layoutExtract.addWidget(self.labelReminder)
        self.layoutExtract.addWidget(self.expParamListWidget)
        # self.layoutExtract.addWidget(self.designerWidget)
        self.layoutExtract.addWidget(self.btn_updateExtractParams)
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
        # Param : Electrode to use for PSD display
        self.electrodePsd = QLineEdit()
        self.electrodePsd.setText('CP3')
        self.formLayoutViz.addRow('Sensor (metric comparison)', self.electrodePsd)
        # Param : Frequency to use for Topography
        self.freqTopo = QLineEdit()
        self.freqTopo.setText('12')
        self.formLayoutViz.addRow('Frequency (Hz) (topomap)', self.freqTopo)
        # Param : checkbox for colormap scaling
        self.colormapScale = QCheckBox()
        self.colormapScale.setTristate(False)
        self.colormapScale.setChecked(True)
        self.formLayoutViz.addRow('Scale Colormap for max contrast', self.colormapScale)
        # Param : checkbox for considering Class2-Class1 sign for AutoFeat
        # self.autofeatUseSign = QCheckBox()
        # self.autofeatUseSign.setTristate(False)
        # self.autofeatUseSign.setChecked(False)
        # self.formLayoutViz.addRow('Class2 > class1 (Colormap and AutoFeat)', self.autofeatUseSign)

        self.autofeatUseSignComboBox = QComboBox()
        self.useSignIdx = 0
        for idxUseSign, key in enumerate(self.useR2SignDict):
            self.autofeatUseSignComboBox.addItem(self.useR2SignDict[key], idxUseSign)
        self.autofeatUseSignComboBox.setCurrentIndex(0)
        self.formLayoutViz.addRow('Consider R2 sign', self.autofeatUseSignComboBox)

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
            metricPsd = "Power Spectral Density (dB)"
            isLogPsd = True
            titleTopo = "Topography of power spectra, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2, False))
            self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq(self.Features, titleTimeFreq))
            self.btn_psd.clicked.connect(lambda: self.btnMetric(self.Features, metricPsd, isLogPsd, titlePsd))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))

            self.btn_r2mapAutoFeat = QPushButton("R² map (sub-select.)")
            self.btn_r2mapAutoFeat.clicked.connect(lambda: self.btnR2(self.Features, titleR2, True))

            self.parallelVizLayouts[0].addWidget(self.btn_r2map)
            self.parallelVizLayouts[0].addWidget(self.btn_r2mapAutoFeat)

            self.parallelVizLayouts[0].addWidget(self.btn_psd)
            self.parallelVizLayouts[0].addWidget(self.btn_timefreq)
            self.parallelVizLayouts[0].addWidget(self.btn_topo)

            self.layoutViz.addLayout(self.parallelVizLayouts[0])

        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # Viz options for "Connectivity" pipeline...
            self.btn_r2map = QPushButton("Display Frequency-channel R² map (NODE STRENGTH)")
            self.btn_timefreq = QPushButton("Display Time-Frequency ERD/ERS analysis")
            self.btn_metric = QPushButton("Display NODE STRENGTH comparison between classes")
            self.btn_topo = QPushButton("Display NODE STRENGTH Brain Topography")
            titleR2 = "Freq.-chan. map of R² values of node strength"
            titleTimeFreq = "Time-Frequency ERD/ERS analysis"
            titleMetric = "Connectivity-based node strength, "
            metricLabel = "Average Node Strength"
            isLogNodeStrength = False
            titleTopo = "Topography of node strengths, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2, False))
            self.btn_metric.clicked.connect(lambda: self.btnMetric(self.Features, metricLabel, isLogNodeStrength, titleMetric))
            self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreqConnect(self.Features, titleTimeFreq))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))

            self.btn_r2mapAutoFeat = QPushButton("R² map (sub-select.)")
            self.btn_r2mapAutoFeat.clicked.connect(lambda: self.btnR2(self.Features, titleR2, True))

            self.parallelVizLayouts[1].addWidget(self.btn_r2map)
            self.parallelVizLayouts[1].addWidget(self.btn_r2mapAutoFeat)

            self.parallelVizLayouts[1].addWidget(self.btn_metric)
            self.parallelVizLayouts[1].addWidget(self.btn_timefreq)
            self.parallelVizLayouts[1].addWidget(self.btn_topo)

            self.layoutViz.addLayout(self.parallelVizLayouts[1])

        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
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
            metricPsd = "Power Spectral Density (dB)"
            isLogPsd = True
            titleTopo = "Topography of power spectra, for freq. "
            self.btn_r2map.clicked.connect(lambda: self.btnR2(self.Features, titleR2, False))
            self.btn_psd.clicked.connect(lambda: self.btnMetric(self.Features, metricPsd, isLogPsd, titlePsd))
            self.btn_topo.clicked.connect(lambda: self.btnTopo(self.Features, titleTopo))

            self.btn_r2mapAutoFeat = QPushButton("R² map (sub-select.)")
            self.btn_r2mapAutoFeat.clicked.connect(lambda: self.btnR2(self.Features, titleR2, True))

            self.parallelVizLayouts[0].addWidget(self.btn_r2map)
            self.parallelVizLayouts[0].addWidget(self.btn_r2mapAutoFeat)
            self.parallelVizLayouts[0].addWidget(self.btn_psd)
            self.parallelVizLayouts[0].addWidget(self.btn_topo)

            # Viz options for "Connectivity" pipeline...
            self.btn_r2map2 = QPushButton("Freq.-chan. R² map")
            self.btn_metric = QPushButton("NodeStr. for the 2 classes")
            self.btn_topo2 = QPushButton("Brain Topography")
            titleR2_c = "Freq.-chan. map of R² values of node strength"
            titleTimeFreq_c = "Time-Frequency ERD/ERS analysis"
            titleMetric_c = "Connectivity-based Node Strength, "
            metricLabel_c = "Average Node Strength"
            isLog_c = False
            titleTopo_c = "Topography of node strengths, for freq. "
            self.btn_r2map2.clicked.connect(lambda: self.btnR2(self.Features2, titleR2_c, False))
            self.btn_metric.clicked.connect(lambda: self.btnMetric(self.Features2, metricLabel_c, isLog_c, titleMetric_c))
            self.btn_topo2.clicked.connect(lambda: self.btnTopo(self.Features2, titleTopo_c))

            self.btn_r2mapAutoFeat2 = QPushButton("R² map (sub-select.)")
            self.btn_r2mapAutoFeat2.clicked.connect(lambda: self.btnR2(self.Features2, titleR2, True))

            self.parallelVizLayouts[1].addWidget(self.btn_r2map2)
            self.parallelVizLayouts[1].addWidget(self.btn_r2mapAutoFeat2)
            self.parallelVizLayouts[1].addWidget(self.btn_metric)
            self.parallelVizLayouts[1].addWidget(self.btn_topo2)

            # Setting up parallel layouts...
            self.parallelVizLayoutH = QHBoxLayout()
            self.parallelVizLayoutH.addLayout(self.parallelVizLayouts[0])
            self.parallelVizLayoutH.addLayout(self.parallelVizLayouts[1])

            self.layoutViz.addLayout(self.labelLayoutH)
            self.layoutViz.addLayout(self.parallelVizLayoutH)

        self.btn_autoFeat = QPushButton("Auto. select optimal features")
        self.btn_autoFeat.clicked.connect(lambda: self.btnAutoFeat(self.Features, self.Features2))
        self.layoutViz.addWidget(self.btn_autoFeat)

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

        self.labelTrain = QLabel('== CLASSIFICATION ==')
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
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
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
        self.selectedFeats[0][0].setText('CP3;8')

        self.btn_addPair = QPushButton("Add feature")
        self.btn_removePair = QPushButton("Remove feature")
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair(self.selectedFeats[0], self.qvFeatureLayouts[0], None))
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair(self.selectedFeats[0], self.qvFeatureLayouts[0]))
        self.qvFeatureLayouts[0].addWidget(self.btn_addPair)
        self.qvFeatureLayouts[0].addWidget(self.btn_removePair)
        self.qvFeatureLayouts[0].addWidget(self.selectedFeats[0][0])

        if self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            self.selectedFeats[1].append(QLineEdit())
            self.selectedFeats[1][0].setText('CP3;8')

            self.btn_addPair2 = QPushButton("Add feature")
            self.btn_removePair2 = QPushButton("Remove feature")
            self.btn_addPair2.clicked.connect(lambda: self.btnAddPair(self.selectedFeats[1], self.qvFeatureLayouts[1], None))
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

        # Classifier training button
        self.btn_trainClassif = QPushButton("TRAIN CLASSIFIER")
        self.btn_trainClassif.clicked.connect(lambda: self.btnTrainClassif())
        self.btn_trainClassif.setStyleSheet("font-weight: bold")
        # Find best combination of features (present only in pipeline 4)
        self.btn_trainClassifCombination = QPushButton("TRAIN - FIND BEST COMB.")
        self.btn_trainClassifCombination.clicked.connect(lambda: self.btnTrainClassifCombination())
        self.btn_trainClassifCombination.setStyleSheet("font-weight: bold")

        # Label + QTreeWidget for training results
        labelLastResults = str("--- Last Training Results ---")
        self.labelLastResults = QLabel(labelLastResults)
        self.labelLastResults.setAlignment(QtCore.Qt.AlignCenter)

        self.lastTrainingResults = QTreeWidget()
        self.lastTrainingResults.setColumnCount(3)
        self.lastTrainingResults.setHeaderLabels(['#', 'Score', 'Feats (expand for details)'])
        self.lastTrainingResults.setColumnWidth(0, 30)
        self.lastTrainingResults.setColumnWidth(1, 60)
        minHeightTrainResults = 30
        self.lastTrainingResults.setMinimumHeight(minHeightTrainResults)
        self.lastTrainingResults.setSelectionMode(QAbstractItemView.SingleSelection)

        # Update training results from config file
        self.updateTrainingAttemptsTree()

        # Connectivity: allow to enable/disable "Speed up" training"
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.enableSpeedUp = QCheckBox()
            self.enableSpeedUp.setTristate(False)
            self.enableSpeedUp.setChecked(False)
            self.enableSpeedUp.setVisible(False)  # advanced option
            speedUpLabel = str("Speed-up training (experimental)")
            self.speedUpLabel = QLabel(speedUpLabel)
            self.speedUpLabel.setAlignment(QtCore.Qt.AlignCenter)
            self.speedUpLabel.setVisible(False)  # advanced option
            self.speedUpLayout = QHBoxLayout()
            self.speedUpLayout.addWidget(self.speedUpLabel)
            self.speedUpLayout.addWidget(self.enableSpeedUp)

        # Use the classif. weights from selected "training attempt" in the list
        self.btn_useSelectedClassif = QPushButton("Use selected classifier (Online scen.)")
        self.btn_useSelectedClassif.clicked.connect(lambda: self.btnUseSelectedClassif())
        self.btn_useSelectedClassif.setStyleSheet("font-weight: bold")

        # Label for classifier running
        labelRunClassif = str("--- Run classification ---")
        self.labelRunClassif = QLabel(labelRunClassif)
        self.labelRunClassif.setAlignment(QtCore.Qt.AlignCenter)
        self.labelRunClassif.setVisible(False)  # advanced option

        # Select files + apply selected classifier
        self.classifLayoutH = QHBoxLayout()
        self.btn_selectFilesClassif = QPushButton("Browse for files...")
        self.btn_selectFilesClassif.setVisible(False) # advanced option
        self.btn_runClassif = QPushButton("RUN CLASSIFIER")
        self.btn_runClassif.setVisible(False) # advanced option
        self.btn_selectFilesClassif.clicked.connect(lambda: self.btnSelectFilesClassif())

        self.btn_runClassif.clicked.connect(lambda: self.btnRunClassif())
        self.classifLayoutH.addWidget(self.btn_selectFilesClassif)
        self.classifLayoutH.addWidget(self.btn_runClassif)

        self.fileListWidgetClassifRun = QTreeWidget()
        self.fileListWidgetClassifRun.setColumnCount(1)
        self.fileListWidgetClassifRun.setHeaderLabels([""])
        self.fileListWidgetClassifRun.setVisible(False) # advanced option

        # Update GUI layout
        self.qvTrainingLayout.addLayout(self.trainingParamsLayout)
        self.qvTrainingLayout.addWidget(self.fileListWidgetTrain)
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.qvTrainingLayout.addLayout(self.speedUpLayout)
        self.qvTrainingLayout.addWidget(self.btn_trainClassif)
        #if self.parameterDict["pipelineType"] == settings.optionKeys[4]:
        self.qvTrainingLayout.addWidget(self.btn_trainClassifCombination)  # Activate later when functional
        self.qvTrainingLayout.addWidget(self.labelLastResults)
        self.qvTrainingLayout.addWidget(self.lastTrainingResults)
        self.qvTrainingLayout.addWidget(self.btn_useSelectedClassif)

        self.qvTrainingLayout.addWidget(self.labelRunClassif)
        self.qvTrainingLayout.addLayout(self.classifLayoutH)
        self.qvTrainingLayout.addWidget(self.fileListWidgetClassifRun)

        self.dlgLayout.addLayout(self.layoutTrain, 1)

        # display initial layout
        self.setLayout(self.dlgLayout)
        self.btn_loadFilesForViz.setEnabled(True)
        self.enablePlotBtns(False)

        self.refreshLists()
        self.updateTrainingAttemptsTree()

        # Timing loop every 4s to get files in working folder
        self.filesRefreshTimer = QtCore.QTimer(self)
        self.filesRefreshTimer.setSingleShot(False)
        self.filesRefreshTimer.setInterval(4000)  # in milliseconds
        self.filesRefreshTimer.timeout.connect(lambda: self.refreshLists())
        self.filesRefreshTimer.start()

    # -----------------------------------------------------------------------
    # CLASS METHODS
    # -----------------------------------------------------------------------
    def enablePlotBtns(self, myBool):
        # ----------
        # Update status of buttons used for plotting
        # ----------

        # Deactivate some buttons for timeflux version
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            self.btn_timefreq.setEnabled(False)

        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.btn_r2map.setEnabled(myBool)
            self.btn_r2mapAutoFeat.setEnabled(myBool)
            if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
                self.btn_timefreq.setEnabled(myBool)
            self.btn_psd.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # self.btn_connectSpect.setEnabled(myBool)
            # self.btn_connectMatrices.setEnabled(myBool)
            # self.btn_connectome.setEnabled(myBool)
            self.btn_timefreq.setEnabled(myBool)
            self.btn_r2map.setEnabled(myBool)
            self.btn_r2mapAutoFeat.setEnabled(myBool)
            self.btn_metric.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            self.btn_r2map.setEnabled(myBool)
            self.btn_r2mapAutoFeat.setEnabled(myBool)
            self.btn_psd.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
            self.btn_r2map2.setEnabled(myBool)
            self.btn_r2mapAutoFeat2.setEnabled(myBool)
            self.btn_metric.setEnabled(myBool)
            self.btn_topo2.setEnabled(myBool)
            if self.parameterDict["pipelineType"] == settings.optionKeys[4]:
                self.btn_r2mapAutoFeat.setEnabled(myBool)
                self.btn_r2mapAutoFeat2.setEnabled(myBool)

        self.btn_autoFeat.setEnabled(myBool)

        self.show()

    def refreshLists(self):
        # ----------
        # Refresh all lists. Called once at the init, then once every timer click (see init method)
        # ----------
        self.refreshSignalList(self.fileListWidget, self.workspaceFolder)
        self.refreshAvailableFilesForVizList(self.workspaceFolder, self.currentSessionId)

        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            self.refreshAvailableTrainSignalList(self.workspaceFolder, self.currentSessionId)
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            self.refreshAvailableTrainSignalList_Timeflux(self.workspaceFolder, self.currentSessionId)

        return

    def refreshSignalList(self, listwidget, workingFolder):
        # ----------
        # Refresh list of available signal (.ov) files
        # ----------
        signalFolder = os.path.join(workingFolder, "signals")

        suffix = ""
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            suffix = ".ov"
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            suffix = ".edf"

        # first get a list of all files in workingfolder that match the condition
        filelist = []
        for filename in os.listdir(signalFolder):
            if filename.endswith(suffix):
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

    def refreshAvailableFilesForVizList(self, workspaceFolder, currentSessionId):
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
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            suffix1 = "-SPECTRUM"
            suffix2 = "-CONNECT"
        suffixFinal = suffix1
        if suffix2:
            suffixFinal += suffix2

        workingFolder = os.path.join(workspaceFolder, "sessions", currentSessionId, "extract")
        class1label = self.parameterDict["AcquisitionParams"]["Class1"]
        class2label = self.parameterDict["AcquisitionParams"]["Class2"]

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
    def refreshAvailableTrainSignalList(self, workspaceFolder, currentSessionId):
        # ----------
        # Refresh available training files.
        # ----------

        workingFolder = os.path.join(workspaceFolder, "sessions", currentSessionId, "train")

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

    def refreshAvailableTrainSignalList_Timeflux(self, workspaceFolder, currentSessionId):
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
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            suffix1 = "-SPECTRUM"
            suffix2 = "-CONNECT"
        suffixFinal = suffix1
        if suffix2:
            suffixFinal += suffix2

        workingFolder = os.path.join(workspaceFolder, "sessions", currentSessionId, "extract")
        class1label = self.parameterDict["AcquisitionParams"]["Class1"]
        class2label = self.parameterDict["AcquisitionParams"]["Class2"]

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
        for x in range(self.fileListWidgetTrain.count() - 1, -1, -1):
            tempitem = self.fileListWidgetTrain.item(x).text()
            if tempitem.removesuffix(suffixFinal) not in availableCsvs:
                self.fileListWidgetTrain.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.fileListWidgetTrain.count()):
            items.append(self.fileListWidgetTrain.item(x).text())
        for basename in availableCsvs:
            basenameSuffix = str(basename+suffixFinal)
            if basenameSuffix not in items:
                self.fileListWidgetTrain.addItem(basenameSuffix)

        return

    # def refreshAvailableTrainSignalList(self, workspaceFolder, currentSessionId):
    #     # ----------
    #     # Refresh available training files.
    #     # ----------

    #     workingFolder = os.path.join(workspaceFolder, "sessions", currentSessionId, "train")

    #     # first get a list of all csv files in workingfolder that match the condition
    #     availableTrainSigs = []
    #     for filename in os.listdir(workingFolder):
    #         if filename.endswith(str("-TRIALS.csv")):
    #             availableTrainSigs.append(filename)

    #     # iterate over existing items in widget and delete those who don't exist anymore
    #     for x in range(self.fileListWidgetTrain.count() - 1, -1, -1):
    #         tempitem = self.fileListWidgetTrain.item(x).text()
    #         if tempitem not in availableTrainSigs:
    #             self.fileListWidgetTrain.takeItem(x)

    #     # iterate over filelist and add new files to listwidget
    #     # for that, create temp list of items in listwidget
    #     items = []
    #     for x in range(self.fileListWidgetTrain.count()):
    #         items.append(self.fileListWidgetTrain.item(x).text())
    #     for filename in availableTrainSigs:
    #         if filename not in items:
    #             self.fileListWidgetTrain.addItem(filename)

    #     return

    def updateExtractParameters(self):
        # ----------
        # Get new extraction parameters
        # return True if params where changed from last known config
        # ----------
        changed = False
        alreadyExists = False
        newId = None
        newDict = self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"].copy()

        # Retrieve param id from label...
        for idx in range(self.layoutExtractLabels.count()):
            paramLabel = self.layoutExtractLabels.itemAt(idx).widget().text()
            # special case : combobox for connectivity metric
            if paramLabel == "Connectivity Estimator":
                paramValue = None
                for k, v in settings.connectMetricsComboText.items():
                    if v == self.layoutExtractLineEdits.itemAt(idx).widget().currentText():
                        paramValue = k
                paramId = list(settings.paramIdText.keys())[list(settings.paramIdText.values()).index(paramLabel)]
            else:
                paramValue = self.layoutExtractLineEdits.itemAt(idx).widget().text()
                paramId = list(settings.paramIdText.keys())[list(settings.paramIdText.values()).index(paramLabel)]

            if self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"][paramId] != paramValue:
                changed = True
                newDict[paramId] = paramValue

        # update json file with new entry and update "current extraction" index
        if changed:
            # find if it's the same as an already existing configuration
            for session in self.parameterDict["Sessions"].keys():
                tempDict = self.parameterDict["Sessions"][session]["ExtractionParams"]
                if newDict == tempDict:
                    self.parameterDict["currentSessionId"] = session
                    setKeyValue(self.workspaceFile, "currentSessionId", self.parameterDict["currentSessionId"])
                    self.currentSessionId = session
                    alreadyExists = True
                    break

            if not alreadyExists:
                # find last idx of extraction parameters
                for session in self.parameterDict["Sessions"].keys():
                    newId = session
                newId = str( int(newId) + 1)
                # save new extraction parameters dict in self.parameterDict
                self.parameterDict["currentSessionId"] = newId
                # write parameters in json file
                newSession(self.workspaceFile, self.parameterDict, newId, newDict)
                setKeyValue(self.workspaceFile, "currentSessionId", self.parameterDict["currentSessionId"])
                # create new folder for future extracted files
                if not os.path.exists(os.path.join(self.workspaceFolder, "sessions", newId)):
                    os.mkdir(os.path.join(self.workspaceFolder, "sessions", newId))
                if not os.path.exists(os.path.join(self.workspaceFolder, "sessions", newId, "extract")):
                    os.mkdir(os.path.join(self.workspaceFolder, "sessions", newId, "extract"))
                if not os.path.exists(os.path.join(self.workspaceFolder, "sessions", newId, "train")):
                    os.mkdir(os.path.join(self.workspaceFolder, "sessions", newId, "train"))
                self.currentSessionId = newId

            # Manually refresh lists
            self.refreshLists()
            self.updateTrainingAttemptsTree()
            # Manually set Visualization part "off", to force user to reload a run
            self.enablePlotBtns(False)

        return changed, alreadyExists, newId

    def runAcquisitionScenario(self):
        # ----------
        # Use acquisition scenario (sc1-monitor-acq.xml) to record
        # EEG signals and Stimulations, as .ov files, using the acquisition parameters
        # set in GUI 1
        # ----------

        signalFolder = os.path.join(self.workspaceFolder, "signals")
        scenFile = os.path.join(self.workspaceFolder, settings.templateScenFilenames[0])

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
        [changed, alreadyExists, newId] = self.updateExtractParameters()

        # Populate list of selected signal files...
        signalFiles = []
        for selectedItem in self.fileListWidget.selectedItems():
            signalFiles.append(selectedItem.text() )
        signalFolder = os.path.join(self.workspaceFolder, "signals")

        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            scenFile = os.path.join(self.workspaceFolder, settings.templateScenFilenames[1])
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            scenFile = os.path.join(self.workspaceFolder, settings.templateScenFilenames_timeflux[0])

        # For each selected signal file, check if extraction has already been done
        # => in .hfw file, at current extract idx, entry exists
        # + extract files exist in corresponding folder
        extractedFiles = loadExtractedFiles(self.workspaceFile, self.currentSessionId)
        redundantFiles = []
        for file in signalFiles:
            if file in extractedFiles:
                # File was found in the list in .hfw config file.
                # Let's see if all extracted files really exist...
                if self.checkExistenceExtractFiles(file):
                    redundantFiles.append(file)

        if len(redundantFiles) > 0:
            for file in redundantFiles:
                retval = myYesNoToAllBox("File " + file + " was already extracted with entered parameters.\nRe-run extraction?")
                if retval == QMessageBox.No:
                    signalFiles.remove(file)
                    if len(signalFiles) == 0:
                        return
                    else:
                        continue
                if retval == QMessageBox.NoToAll:
                    signalFiles = []
                    return
                if retval == QMessageBox.YesToAll:
                    break

        # Add extracted files to .hfw config file
        # TODO : put somewhere else, AFTER extraction has succeeded...
        for file in signalFiles:
            addExtractedFile(self.workspaceFile, self.currentSessionId, file)

        # create progress bar window...
        self.progressBarExtract = ProgressBar("Feature extraction",
                                              str("Extracting data for file "+signalFiles[0]+"..."),
                                              len(signalFiles))

        # deactivate this part of the GUI
        self.enableExtractionGui(False)

        # deactivate automatic file refresh, or else we might get .csv files in
        # the viz and train lists before they're ready to be used
        self.filesRefreshTimer.stop()

        # Instantiate the thread...
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            self.extractThread = Extraction(self.ovScript, scenFile, signalFiles, signalFolder, self.parameterDict, self.currentSessionId)
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            self.extractThread = Extraction_Timeflux(scenFile, signalFiles, signalFolder, self.parameterDict, self.currentSessionId)

        # Signal: Extraction work thread finished one file of the selected list.
        # Refresh the viz&train file lists to make it available + increment progress bar
        self.extractThread.info.connect(self.progressBarExtract.increment)
        self.extractThread.info.connect(lambda : self.refreshLists())
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
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            suffix = "-SPECTRUM-CONNECT"

        analysisFiles = []
        for selectedItem in self.availableFilesForVizList.selectedItems():
            analysisFiles.append(selectedItem.text().removesuffix(suffix))
        workingFolder = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "extract")
        metaFolder = os.path.join(self.workspaceFolder, "signals")
        # deactivate this part of the GUI + the extraction (or else we might have sync issues)
        self.enableExtractionGui(False)
        self.enableVizGui(False)

        # Instantiate the thread...
        # TODO : refactor using automatic feature selection possibility
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
                self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, workingFolder, self.parameterDict, self.Features, self.samplingFreq)
            elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
                self.loadFilesForVizThread = LoadFilesForVizConnectivity(analysisFiles, workingFolder, metaFolder, self.parameterDict, self.Features, self.samplingFreq)
            elif self.parameterDict["pipelineType"] == settings.optionKeys[3]:
                self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, workingFolder, self.parameterDict, self.Features, self.samplingFreq)
                self.loadFilesForVizThread2 = LoadFilesForVizConnectivity(analysisFiles, workingFolder, metaFolder, self.parameterDict, self.Features2, self.samplingFreq)
            elif self.parameterDict["pipelineType"] == settings.optionKeys[4]:
                self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, workingFolder, self.parameterDict, self.Features, self.samplingFreq)
                self.loadFilesForVizThread2 = LoadFilesForVizConnectivity(analysisFiles, workingFolder, metaFolder, self.parameterDict, self.Features2, self.samplingFreq)

        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
                self.loadFilesForVizThread = LoadFilesForVizPowSpectrum_Timeflux(analysisFiles, workingFolder, self.parameterDict, self.Features, self.samplingFreq)
            else:
                myMsgBox(str("Pipeline " + self.parameterDict["pipelineType"] + " is not available with Timeflux") )
                return

        # create progress bar window...
        self.progressBarViz = ProgressBar("Feature Visualization", "Loading data from Csv files...",
                                          len(self.availableFilesForVizList.selectedItems()))
        # Signal: Viz work thread finished one file of the selected list.
        # Increment progress bar + its label
        self.loadFilesForVizThread.info.connect(self.progressBarViz.increment)
        self.loadFilesForVizThread.info2.connect(self.progressBarViz.changeLabel)
        # Signal: Viz work thread finished
        self.loadFilesForVizThread.over.connect(self.loadFilesForViz_over)

        # Manage number of threads (for GUI reactivation...)
        self.nbThreadsViz = 1
        self.vizThreadStatus = []

        # Launch the work thread
        self.loadFilesForVizThread.start()

        if self.loadFilesForVizThread2:
            self.nbThreadsViz = 2
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

    def loadFilesForViz_over(self, success, text, fileValidityList, initWindowsList, validWindowsList):
        # Viz work thread is over, so we kill the progress bar,
        # and re-activate the GUI (if it's the last thread to finish)
        self.vizTimerEnd = time.perf_counter()
        elapsed = self.vizTimerEnd - self.vizTimerStart
        print("=== Viz data loaded in: ", str(elapsed))

        self.progressBarViz.finish()

        if not success:
            myMsgBox(text)
            self.vizThreadStatus.append(False)
        else:
            self.samplingFreq = self.Features.samplingFreq
            self.vizThreadStatus.append(True)

        # unlock viz buttons only if both threads have finished.
        self.lockVizGui.acquire()
        try:
            self.nbThreadsViz -= 1
            if self.nbThreadsViz == 0:
                if False in self.vizThreadStatus:
                    self.plotBtnsEnabled = False
                else:
                    self.plotBtnsEnabled = True

                self.enableGui(True)

        finally:
            self.lockVizGui.release()

        # Handle case in which we had to prune out trials with invalid values (NaN)
        if not all(fileValidityList):
            analysisFiles = []
            for selectedItem in self.availableFilesForVizList.selectedItems():
                analysisFiles.append(selectedItem.text())
            invalidFiles = [i for i in range(len(fileValidityList)) if not fileValidityList[i]]
            warnText = str("--Warning: the following files contained invalid values (NaN).\n")
            warnText += str("\nTrials with invalid values were dropped.")
            warnText += str("\n /!\\ The displayed statistics (R2 maps, etc.) might be biased...\n")
            for i in invalidFiles:
                warnText += str("\n" + analysisFiles[i] + ": ")
                warnText += str(str(validWindowsList[i]) + "/" + str(initWindowsList[i]) )
                warnText += str(" valid windows")

            myMsgBox(warnText)

    def loadFilesForViz_kill_PB(self, success, text, fileValidityList, initWindowsList, validWindowsList):
        # Viz work thread2 is over, so we kill the progress bar
        # and re-activate the GUI (if it's the last thread to finish)
        self.progressBarViz2.finish()

        if not success:
            myMsgBox(text)
            self.vizThreadStatus.append(False)
        else:
            self.samplingFreq = self.Features.samplingFreq
            self.vizThreadStatus.append(True)

        # unlock viz buttons only if both threads have finished.
        self.lockVizGui.acquire()
        try:
            self.nbThreadsViz -= 1
            if self.nbThreadsViz == 0:
                if False in self.vizThreadStatus:
                    self.plotBtnsEnabled = False
                else:
                    self.plotBtnsEnabled = True

                self.enableGui(True)

        finally:
            self.lockVizGui.release()

        # Handle case in which we had to prune out trials with invalid values (NaN)
        if not all(fileValidityList):
            analysisFiles = []
            for selectedItem in self.availableFilesForVizList.selectedItems():
                analysisFiles.append(selectedItem.text())
            invalidFiles = [i for i in range(len(fileValidityList)) if not fileValidityList[i]]
            warnText = str("--Warning: the following files contained invalid values (NaN).\n")
            warnText += str("\nTrials with invalid values were dropped.")
            warnText += str("\n /!\\ The displayed statistics (R2 maps, etc.) might be biased...\n")
            for i in invalidFiles:
                warnText += str("\n" + analysisFiles[i] + ": ")
                warnText += str(str(validWindowsList[i]) + "/" + str(initWindowsList[i]))
                warnText += str(" valid windows")

            myMsgBox(warnText)

    def btnTrainClassif(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # provide the classification score/accuracy as a textbox
        # ----------

        # TODO : REFACTOR TO BETTER MERGE OPENVIBE/TIMEFLUX BRANCHES

        if not self.fileListWidgetTrain.selectedItems():
            myMsgBox("Please select a set of files for training")
            return

        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # case with 1 set of features...
            if len(self.selectedFeats[0]) < 1:
                myMsgBox("Please use at least one set of features!")
                return
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            # case with 2 sets of features : one of the two can be empty
            if len(self.selectedFeats[0]) < 1 and len(self.selectedFeats[1]) < 1:
                myMsgBox("Please use at least one set of features!")
                return

        # Get training param from GUI (to modify training scenario later on)
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

        # 1-class specific case: check if "baseline" files also exist
        if self.parameterDict["pipelineType"] == optionKeys[4]:
            for trainingFile in self.trainingFiles:
                baselineFile = trainingFile.replace("TRIALS", "BASELINE")
                if not os.path.exists(os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", baselineFile)):
                    myMsgBox("Error in training: missing BASELINE file. Check your workspace folder and extraction scenario")
                    return

        # Initialize structure for reporting results in workspace file...
        self.currentAttempt = {"SignalFiles": self.trainingFiles,
                                  "CompositeFile": None, "Features": None, "Score": ""}

        # LOAD TRAINING FEATURES
        # /!\ IMPORTANT !
        # When using "mixed" pipeline, if one of the two feature lists is empty, we use
        # the Training scenario template from the pipeline with the non-empty feature (got it?)
        # ex: if feats(connectivity) is empty, then we use the "powerspectrum" template.
        trainingParamDict = self.parameterDict.copy()
        listFeats = []
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            for featWidget in self.selectedFeats[0]:
                listFeats.append(featWidget.text())
            self.currentAttempt["Features"] = {self.parameterDict["pipelineType"]: listFeats}
        else:
            # save which features have been selected for which features. Include cases in which
            # features for only one of the two metrics have been selected
            if len(self.selectedFeats[0]) < 1:
                # no powspectum feature = use connectivity pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[2]
                # copy the selected feats to the first list, for processing in the thread...
                for featWidget in self.selectedFeats[1]:
                    listFeats.append(featWidget.text())
                self.currentAttempt["Features"] = {settings.optionKeys[2]: listFeats}
            elif len(self.selectedFeats[1]) < 1:
                # no connectivity feature = use powspectrum pipeline's training template
                trainingParamDict["pipelineType"] = settings.optionKeys[1]
                for featWidget in self.selectedFeats[0]:
                    listFeats.append(featWidget.text())
                self.currentAttempt["Features"] = {settings.optionKeys[1]: listFeats}
            else:
                # save both features
                listFeats = [[], []]
                for metric in [0, 1]:
                    for featWidget in self.selectedFeats[metric]:
                        listFeats[metric].append(featWidget.text())
                self.currentAttempt["Features"] = {settings.optionKeys[1]: listFeats[0],
                                                      settings.optionKeys[2]: listFeats[1]}

        # Check if training with such parameters has already been attempted
        alreadyAttempted, attemptId, score = \
            checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                       self.currentAttempt["SignalFiles"],
                                       self.currentAttempt["Features"])
        if alreadyAttempted:
            message = str("Training was already attempted (id " + attemptId + ") ")
            message += str("\nwith an accuracy of " + score + " %")
            message += str("\n\tRun it again?")
            retVal = myOkCancelBox(message)
            if retVal == QMessageBox.Cancel:
                self.currentAttempt = []
                return

        # deactivate this part of the GUI (+ the extraction part)
        self.enableExtractionGui(False)
        self.enableTrainGui(False)

        # create progress bar window...
        self.progressBarTrain = ProgressBar("Classifier training", "Creating composite file", 2)

        # Instantiate the thread...
        combiComp = False
        signalFolder = os.path.join(self.workspaceFolder, "signals")

        enableSpeedUp = False
        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            if self.enableSpeedUp.isChecked():
                enableSpeedUp = True

        templateFolder = settings.optionsTemplatesDir[trainingParamDict["pipelineType"]]

        # Parametrize Train Thread, depending on the platform
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            self.trainClassThread.append(TrainClassifier(self.trainingFiles,
                                                         signalFolder, templateFolder,
                                                         self.workspaceFolder,
                                                         self.ovScript,
                                                         trainingSize, listFeats,
                                                         trainingParamDict, self.samplingFreq,
                                                         self.currentAttempt, attemptId,
                                                         enableSpeedUp))

        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux

            suffix = ""
            if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
               suffix = "-SPECTRUM"
            elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
                suffix = "-CONNECT"
                myMsgBox(str("Pipeline not available. What are you even doing here?"))
                return
            elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                     or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
                suffix = "-SPECTRUM-CONNECT"
                myMsgBox(str("Pipeline not available. What are you even doing here?"))
                return

            # TODO : REFACTOR THIS PART !
            trainFiles = []
            for selectedItem in self.fileListWidgetTrain.selectedItems():
                trainFiles.append(selectedItem.text().removesuffix(suffix))
            print("Timeflux: training features list: ", listFeats)

            # Transforming the list
            filter_list = [item.split(';') for item in listFeats]

            # Convert the second element of each sublist to an integer
            filter_list = [[ele[0], int(ele[1])] for ele in filter_list]
            print(filter_list)

            # TODO : REVIEW HOW THE SCEN / TEMPLATES ARE MANAGED BETWEEN HERE AND THREADS.PY
            scenFile = os.path.join(self.workspaceFolder, settings.templateScenFilenames_timeflux[1])

            model_file_path = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train",
                                           str("classifier-weights-" + str(attemptId) + ".pkl"))

            trainThread = TrainClassifier_Timeflux(scenFile,
                                                 trainFiles,
                                                 self.workspaceFolder,
                                                 self.parameterDict,
                                                 self.currentSessionId,
                                                 filter_list,
                                                 trainingSize,
                                                 self.currentAttempt,
                                                 attemptId,
                                                 model_file_path,
                                                 parent=self)

            self.trainClassThread.append(trainThread)

        # Signal: Training work thread finished one step
        # Increment progress bar + change its label
        self.trainClassThread[0].info.connect(self.progressBarTrain.increment)
        self.trainClassThread[0].info2.connect(self.progressBarTrain.changeLabel)

        # Signal: Training work thread finished
        self.trainClassThread[0].over.connect(self.training_over)

        # Launch the work thread
        self.trainClassThread[0].start()

        self.trainTimerStart = time.perf_counter()

    def training_over(self, success, attemptIdTemp, resultsText):
        # Training work thread is over, so we kill the progress bar,
        # display a msg with results, and make the training Gui available again
        self.trainTimerEnd = time.perf_counter()
        elapsed = self.trainTimerEnd - self.trainTimerStart
        print("=== Training done in: ", str(elapsed))
        self.trainClassThread.clear()

        self.progressBarTrain.finish()
        if success:
            # Add training attempt in workspace file
            print("=== Checking if attempt already done...")
            alreadyDone, attemptId, dummy = \
                checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                           self.currentAttempt["SignalFiles"],
                                           self.currentAttempt["Features"])
            if alreadyDone:
                print("=== replaceTrainingAttempt...")
                replaceTrainingAttempt(self.workspaceFile, self.currentSessionId, attemptId,
                                       self.currentAttempt["SignalFiles"], self.currentAttempt["CompositeFile"],
                                       self.currentAttempt["Features"], self.currentAttempt["Score"])
            else:
                print("=== addTrainingAttempt...")
                addTrainingAttempt(self.workspaceFile, self.currentSessionId,
                                       self.currentAttempt["SignalFiles"], self.currentAttempt["CompositeFile"],
                                       self.currentAttempt["Features"], self.currentAttempt["Score"])
            print("=== updateTrainingAttemptsTree...")
            self.updateTrainingAttemptsTree()

            textGoodbye = str("Classifier weights were written in:\n\t")
            textGoodbye += self.workspaceFolder + str("/classifier-weights.xml\n")
		    # textGoodbye += self.workspaceFolder + str("/fitted_model.pkl\n") # TIMEFLUX
            textGoodbye += str("If those results are satisfying, you can now open in the OV Designer:\n\t") \
                           + self.workspaceFolder + str("/sc3-online.xml in the Designer")

            textDisplayed = str(resultsText + "\n\n" + textGoodbye)
            msg = QMessageBox()
            msg.setText(textDisplayed)
            msg.setStyleSheet("QLabel{min-width: 1200px;}")
            msg.setWindowTitle("Classifier Training Score")
            msg.exec()
        else:
            myMsgBox(resultsText)
        self.enableGui(True)

    def btnTrainClassifCombination(self):
        # ----------
        # Callback from button :
        # Select features in fields, check if they're correctly formatted,
        # launch openvibe with sc2-train.xml (in the background) to train the classifier,
        # for as many combinations of Features possible
        # (if one metric type : (1), (1+2), (1+2+3) )
        # (if two metrics : (1+1) , (1+2 + 1+2), (1+2+3 + 1+2+3) )
        #
        # provide the classification score/accuracy as a textbox
        # ----------

        # basic checks
        if not self.fileListWidgetTrain.selectedItems():
            myMsgBox("Please select a set of files for training")
            return

        if len(self.selectedFeats[0]) < 1:
            myMsgBox("Please use at least one set of features!")
            return

        if self.parameterDict["pipelineType"] == settings.optionKeys[3]\
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            # the 2 sets of features must have the same (>0) size
            if len(self.selectedFeats[0]) != len(self.selectedFeats[1]):
                myMsgBox("Please use the same number of PSD and NS feats (>0)")
                return

        # Get training param from GUI (to modify training scenario later on)
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

        # 1-class specific case: check if "baseline" files also exist
        if self.parameterDict["pipelineType"] == optionKeys[4]:
            for trainingFile in self.trainingFiles:
                baselineFile = trainingFile.replace("TRIALS", "BASELINE")
                if not os.path.exists(os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", baselineFile)):
                    myMsgBox("Error in training: missing BASELINE file. Check your workspace folder and extraction scenario")
                    return

        # Initialize structure for reporting results in workspace file...
        tempAttempt = {"SignalFiles": self.trainingFiles,
                       "CompositeFile": None, "Features": None, "Score": ""}
        self.currentAttempt = [] 
        for comb in range(len(self.selectedFeats[0])):
            self.currentAttempt.append(tempAttempt.copy())

        # LOAD TRAINING FEATURES
        # /!\ IMPORTANT !
        # When using "mixed" pipeline, if one of the two feature lists is empty, we use
        # the Training scenario template from the pipeline with the non-empty feature (got it?)
        # ex: if feats(connectivity) is empty, then we use the "powerspectrum" template.
        trainingParamDict = self.parameterDict.copy()
        listFeats = []
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            for featWidget in self.selectedFeats[0]:
                listFeats.append(featWidget.text())
            listFeatsTemp = listFeats.copy()  # copy the list so that we don't lose it when exiting the scope...
            for comb in range(len(self.selectedFeats[0])):
                self.currentAttempt[comb]["Features"] = {self.parameterDict["pipelineType"]: list(listFeatsTemp)}
                listFeatsTemp.pop()  # remove last element. Next iteration has 1 less element, etc.

        else:
            # save both features
            listFeats = [[], []]
            listFeatsTemp = [[], []]
            for metric in [0, 1]:
                for featWidget in self.selectedFeats[metric]:
                    listFeats[metric].append(featWidget.text())
                listFeatsTemp[metric] = listFeats[metric].copy()
            for comb in range(len(self.selectedFeats[0])):
                self.currentAttempt[comb]["Features"] = {settings.optionKeys[1]: list(listFeatsTemp[0]),
                                                         settings.optionKeys[2]: list(listFeatsTemp[1])}
                listFeatsTemp[0].pop()
                listFeatsTemp[1].pop()  # remove last element. Next iteration has 1 less element, etc.

        # Check if training with such parameters has already been attempted
        # (check only for case with all features)
        alreadyAttempted, attemptId, score = \
            checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                       self.currentAttempt[0]["SignalFiles"],
                                       self.currentAttempt[0]["Features"])
        if alreadyAttempted:
            message = str("Training was already attempted (id " + attemptId + ") ")
            message += str("\nwith an accuracy of " + score + " %")
            message += str("\n\tRun it again?")
            retVal = myOkCancelBox(message)
            if retVal == QMessageBox.Cancel:
                self.currentAttempt = []
                return

        # deactivate this part of the GUI (+ the extraction part)
        self.enableExtractionGui(False)
        self.enableTrainGui(False)

        # create progress bar window...
        self.progressBarTrainCombination = ProgressBar("Classifier training", "Combination ... ", len(self.selectedFeats[0]))

        # a few common inits...
        signalFolder = os.path.join(self.workspaceFolder, "signals")
        templateFolder = settings.optionsTemplatesDir[trainingParamDict["pipelineType"]]
        enableSpeedUp = False
        # if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
        #     if self.enableSpeedUp.isChecked():
        #         enableSpeedUp = True

        for comb in range(len(self.selectedFeats[0])):

            # Load the specific set of features for this combination
            if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                    or self.parameterDict["pipelineType"] == settings.optionKeys[2]:

                listFeats = self.currentAttempt[comb]["Features"][self.parameterDict["pipelineType"]]

            else:
                listFeats[0] = self.currentAttempt[comb]["Features"][settings.optionKeys[1]]
                listFeats[1] = self.currentAttempt[comb]["Features"][settings.optionKeys[2]]

            # we use "check if already done" again, not to prompt the user, but to get
            # a valid "attemptId"
            alreadyAttempted, attemptId, score = \
                checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                           self.currentAttempt[comb]["SignalFiles"],
                                           self.currentAttempt[comb]["Features"])

            # we add (empty) training attempts corresponding to the id. Otherwise
            # all tested combinations would have the same ID!
            # They will get replaced in trainingCombination_over() method
            addTrainingAttempt(self.workspaceFile, self.currentSessionId,
                               self.currentAttempt[comb]["SignalFiles"],
                               None,
                               self.currentAttempt[comb]["Features"],
                               "0.0")

            # Instantiate the thread...
            self.trainClassThread.append( TrainClassifier(  self.trainingFiles,
                                                            signalFolder, templateFolder,
                                                            self.workspaceFolder,
                                                            self.ovScript,
                                                            trainingSize, listFeats,
                                                            trainingParamDict, self.samplingFreq,
                                                            self.currentAttempt[comb], attemptId,
                                                            enableSpeedUp) )


        # Launch the first (or only) thread.
        # Launching/management of upcoming threads in "trainingcombination_over"
        self.trainClassThread[0].over.connect(self.trainingCombination_over)
        self.trainClassThread[0].start()
        self.currentTrainCombination = 0
        self.trainTimerStart = time.perf_counter()

    def trainingCombination_over(self, success, attemptIdTemp, resultsText):
        # Training work thread is over, so we update (or kill) the progress bar,
        # display a msg with results at the end of all attemps,
        # and make the training Gui available again

        lastCombination = False
        # Update or kill the progress bar, and the global training timer
        if(self.currentTrainCombination < len(self.selectedFeats[0])-1):
            self.progressBarTrainCombination.increment()
        else:
            self.progressBarTrainCombination.finish()
            self.trainTimerEnd = time.perf_counter()
            elapsed = self.trainTimerEnd - self.trainTimerStart
            print("=== Training done in: ", str(elapsed))
            self.trainClassThread.clear()
            lastCombination = True

        if success:

            comb = self.currentTrainCombination
            # Add training attempt in workspace file
            alreadyDone, attemptId, dummy = \
                checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                           self.currentAttempt[comb]["SignalFiles"],
                                           self.currentAttempt[comb]["Features"])
            if alreadyDone:
                replaceTrainingAttempt(self.workspaceFile, self.currentSessionId, attemptId,
                                       self.currentAttempt[comb]["SignalFiles"],
                                       self.currentAttempt[comb]["CompositeFile"],
                                       self.currentAttempt[comb]["Features"],
                                       self.currentAttempt[comb]["Score"])
            else:
                addTrainingAttempt(self.workspaceFile, self.currentSessionId,
                                   self.currentAttempt[comb]["SignalFiles"],
                                   self.currentAttempt[comb]["CompositeFile"],
                                   self.currentAttempt[comb]["Features"],
                                   self.currentAttempt[comb]["Score"])

            self.updateTrainingAttemptsTree()

            # Launch next thread if necessary
            if not lastCombination:
                self.currentTrainCombination += 1
                self.trainClassThread[self.currentTrainCombination].over.connect(self.trainingCombination_over)
                self.trainClassThread[self.currentTrainCombination].start()

        else:
            myMsgBox(resultsText)

        if lastCombination:

            trainingFilesList = self.currentAttempt[comb]["SignalFiles"]
            exitText = str("== COMBINATION TRAINING RESULTS ==\n\n")
            exitText += str("Using files:\n")
            for i in range(len(trainingFilesList)):
                exitText += str(trainingFilesList[i] + "\n")
            exitText += str("\n")

            bestScore = 0.0
            bestAttempt = 0
            bestFeatures = ""
            for comb in range(len(self.selectedFeats[0])):
                if float(self.currentAttempt[comb]["Score"]) > bestScore:
                    bestScore = float(self.currentAttempt[comb]["Score"])
                    alreadyDone, attemptId, dummy = \
                        checkIfTrainingAlreadyDone(self.workspaceFile, self.currentSessionId,
                                                   self.currentAttempt[comb]["SignalFiles"],
                                                   self.currentAttempt[comb]["Features"])
                    bestAttempt = attemptId
                    bestFeatures = self.currentAttempt[comb]["Features"]

                feats = self.currentAttempt[comb]["Features"]
                exitText += "Features: "
                # for i in range(len(feats)):
                #     exitText += str(feats[i] + " ")
                exitText += str(feats)
                exitText += str("\n")
                exitText += str("Score: " + str(self.currentAttempt[comb]["Score"]))
                exitText += str("\n")

            exitText += str("\n")
            exitText += str("== Best score: " + str(bestScore) + ", with attempt id " + str(bestAttempt) + "\n")
            exitText += str("   and Features: " + str(bestFeatures) + "\n\n")

            exitText += str("Use the button \"Use selected classifier\" to edit sc3-online.xml with the classifier weights and parameters of your choice.")

            msg = QMessageBox()
            msg.setText(exitText)
            msg.setStyleSheet("QLabel{min-width: 1200px;}")
            msg.setWindowTitle("Classifier Training Score")
            msg.exec()

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
        self.btn_updateExtractParams.setEnabled(myBool)
        self.fileListWidget.setEnabled(myBool)
        # self.btn_browseOvScript.setEnabled(myBool)
        self.menuOptions.setEnabled(myBool)

    def enableVizGui(self, myBool):
        # Viz part...
        self.btn_loadFilesForViz.setEnabled(myBool)
        self.availableFilesForVizList.setEnabled(myBool)

        self.electrodePsd.setEnabled(myBool)
        self.freqTopo.setEnabled(myBool)
        self.colormapScale.setEnabled(myBool)
        # self.autofeatUseSign.setEnabled(myBool)
        self.autofeatUseSignComboBox.setEnabled(myBool)

        self.btn_loadFilesForViz.setEnabled(myBool)
        if myBool and self.plotBtnsEnabled:
            self.enablePlotBtns(True)
        if not myBool:
            self.enablePlotBtns(False)

    def enableTrainGui(self, myBool):
        # Training part...
        self.btn_addPair.setEnabled(myBool)
        self.btn_removePair.setEnabled(myBool)
        self.btn_trainClassif.setEnabled(myBool)
        self.btn_trainClassifCombination.setEnabled(myBool)
        for listOfFeatures in self.selectedFeats:
            for item in listOfFeatures:
                item.setEnabled(myBool)
        self.trainingPartitions.setEnabled(myBool)
        self.fileListWidgetTrain.setEnabled(myBool)
        self.menuOptions.setEnabled(myBool)
        self.btn_runClassif.setEnabled(myBool)
        self.btn_selectFilesClassif.setEnabled(myBool)

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
        newDict = getExperimentalParameters(self.workspaceFile)
        if not newDict:
            newDict = settings.pipelineAcqSettings.copy()
            # todo : ask user to use GUI 1 ! it's not normal that
            # todo (cont): ... experimental parameters are missing at this point

        print(newDict)
        return newDict

    def getDefaultExtractionParameters(self):
        # ----------
        # Get "extraction" parameters from the JSON parameters
        # A bit artisanal, but we'll see if we keep that...
        # ----------
        pipelineKey = self.parameterDict['pipelineType']
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            newDict = settings.pipelineExtractSettings_ov[pipelineKey].copy()
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            newDict = settings.pipelineExtractSettings_tf[pipelineKey].copy()

        print(newDict)
        return newDict

    # Plot R2 map using Visualization_Data functions
    def btnR2(self, features, title, useSubselection):
        if checkFreqsMinMax(self.userFmin, self.userFmax, self.samplingFreq):
            each_point = 1  # Todo : make parameter?

            # if "consider the sign of Class2-Class1" is checked,
            # modify the R2 to display
            tempR2 = features.Rsquare.copy()

            useSign = self.autofeatUseSignComboBox.currentIndex()
            if useSign > 0:
                tempRsign = features.Rsign_tab.copy()
                if useSign == 2:
                    # reverse the sign for the Rsquare map...
                    tempRsign[np.where(features.Rsign_tab < 0)] = 1
                    tempRsign[np.where(features.Rsign_tab > 0)] = -1
                tempR2 = tempR2 * tempRsign

            # Full map
            if not useSubselection:
                fig = plot_Rsquare_plotly(tempR2,
                                          np.array(features.electrodes_final)[:],
                                          features.freqs_array,
                                          features.fres,
                                          each_point,
                                          self.userFmin,
                                          self.userFmax,
                                          self.colormapScale.isChecked(),
                                          (useSign > 0),
                                          title)
                filename = str(self.workspaceFolder + "/lastfigure.html")
                plotly.offline.plot(fig, filename=filename, auto_open=True)


            # Map subselection
            else:
                subR2 = []
                subElectrodes = []
                freqMin = int(self.autoFeatFreqRange.split(":")[0])
                freqMax = int(self.autoFeatFreqRange.split(":")[1])
                # freqRange = np.arange(round(freqMin/features.fres), round(freqMax/features.fres)+1, features.fres)
                for chan in self.autoFeatChannelList:
                    try:
                        # subR2.append(features.Rsquare[features.electrodes_final.index(chan), freqMin:(freqMax+1)])
                        subR2.append(tempR2[features.electrodes_final.index(chan), :])
                    except ValueError:
                        myMsgBox("Invalid electrode subselection or frequency range for auto. feature selection")
                        return
                    subElectrodes.append(chan)

                subR2 = np.array(subR2)

                fig = plot_Rsquare_plotly(subR2,
                                          np.array(subElectrodes)[:],
                                          features.freqs_array,
                                          features.fres,
                                          each_point,
                                          freqMin,
                                          freqMax,
                                          self.colormapScale.isChecked(),
                                          (useSign > 0),
                                          title)

                filename = str(self.workspaceFolder + "/lastfigure.html")
                plotly.offline.plot(fig, filename=filename, auto_open=True)

    # Wilcoxon Map. Not used - TODO : delete?
    def btnW2(self, features, title):
        if checkFreqsMinMax(self.userFmin, self.userFmax, self.samplingFreq):
            smoothing = False
            each_point = 1
            plot_Rsquare_calcul_welch(features.Wsigned,
                                      np.array(features.electrodes_final)[:],
                                      features.freqs_array,
                                      smoothing,
                                      features.fres,
                                      each_point,
                                      self.userFmin,
                                      self.userFmax,
                                      self.colormapScale.isChecked(),
                                      title)
            plt.show()

    # Btn callback: Plot "time-frequency analysis", in the POWER SPECTRUM pipeline ONLY.
    def btnTimeFreq(self, features, title):
        if checkFreqsMinMax(self.userFmin, self.userFmax, self.samplingFreq):
            print("TimeFreq for sensor: " + self.electrodePsd.text())

            tmin = float(self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"]['StimulationDelay'])
            tmax = float(self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"]['StimulationEpoch'])
            fmin = self.userFmin
            fmax = self.userFmax
            class1 = self.parameterDict["AcquisitionParams"]["Class1"]
            class2 = self.parameterDict["AcquisitionParams"]["Class2"]

            self.plot_tf(features.timefreq_cond1, features.timefreq_cond2,
                         features.time_array, features.freqs_array,
                         self.electrodePsd.text(), features.fres,
                         features.average_baseline_cond1, features.average_baseline_cond2,
                         features.std_baseline_cond1, features.std_baseline_cond2,
                         features.electrodes_final,
                         fmin, fmax, tmin, tmax, class1, class2, title)

    # interface for btnTimeFreq
    # TODO : reorganize/refactor with Visualization_Data.py
    def plot_tf(self, timefreq_cond1, timefreq_cond2, time_array, freqs_array, electrode, fres, average_baseline_cond1, average_baseline_cond2, std_baseline_cond1, std_baseline_cond2, electrodes, f_min_var, f_max_var, tmin, tmax, class1label, class2label, title):
        font = {'family': 'serif',
                'color': 'black',
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
                A.append(np.divide((tf[:, i] - PSD_baseline), PSD_baseline) * 100)
            tf = np.transpose(A)
            vmin = np.amin(tf[f_min_var:f_max_var, :])
            vmax = np.amax(tf[f_min_var:f_max_var, :])
            tlength = tmax - tmin
            time_frequency_map(timefreq_cond1, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10,
                               average_baseline_cond1, electrodes, std_baseline_cond1, vmin, vmax, tlength)
            plt.title(title + '(' + class1label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
            time_frequency_map(timefreq_cond2, time_array, freqs_array, Index_electrode, fmin, fmax, fres, 10,
                               average_baseline_cond2, electrodes, std_baseline_cond2, vmin, vmax, tlength)
            plt.title(title + '(' + class2label + ') Sensor ' + electrodes[Index_electrode], fontdict=font)
            plt.show()

    # Btn Callback: Plot "time-frequency analysis", in the CONNECTIVITY pipeline ONLY.
    def btnTimeFreqConnect(self, features, title):
        if checkFreqsMinMax(self.userFmin, self.userFmax, self.samplingFreq):
            print("TimeFreq for sensor: " + self.electrodePsd.text())

            tmin = float(self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"]['StimulationDelay'])
            tmax = float(self.parameterDict["Sessions"][self.currentSessionId]["ExtractionParams"]['StimulationEpoch'])
            fmin = self.userFmin
            fmax = self.userFmax
            class1 = self.parameterDict["AcquisitionParams"]["Class1"]
            class2 = self.parameterDict["AcquisitionParams"]["Class2"]

            self.plot_tf_connect(features.timefreq_cond1, features.timefreq_cond2,
                                 features.time_array, features.freqs_array,
                                 self.electrodePsd.text(), features.fres,
                                 features.electrodes_final,
                                 fmin, fmax, tmin, tmax, class1, class2, title)

    # interface for btnTimeFreqConnect
    # TODO : reorganize/refactor with Visualization_Data.py
    def plot_tf_connect(self, timefreq_cond1, timefreq_cond2, time_array, freqs_array, electrode, fres, electrodes,
                        f_min_var, f_max_var, tmin, tmax, class1label, class2label, title):
        font = {'family': 'serif',
                'color': 'black',
                'weight': 'normal',
                'size': 14,
                }
        fmin = int(f_min_var / fres)
        fmax = int(f_max_var / fres)

        Test_existing = False
        idx = 0
        for i in range(len(electrodes)):
            if electrodes[i] == electrode:
                idx = i
                Test_existing = True
        if not Test_existing:
            myMsgBox("No Electrode with this name found")
        else:
            tf = (timefreq_cond1.mean(0) - timefreq_cond2.mean(0)) / timefreq_cond1.mean(0)
            tf = tf.transpose(0, 2, 1)

        fig, ax = plt.subplots()
        im = ax.imshow(tf[idx, fmin:fmax, :], cmap='jet', origin='lower', aspect='auto',
                       vmin=- np.nanmax(abs(tf[idx, fmin:fmax, :])),
                       vmax=np.nanmax(abs(tf[idx, fmin:fmax, :])), interpolation="hanning")

        time_increments = (tmax - tmin) / np.shape(tf)[2]
        time_series = np.around(np.arange(tmin, tmax, time_increments), 2)
        freq_series = np.arange(f_min_var, f_max_var + 1, int(f_max_var - f_min_var) / 10)
        ax.set_xticks(np.arange(0, np.shape(tf)[2], 1))
        ax.set_xticklabels(time_series, rotation=90)
        ax.set_yticks(np.arange(fmin, fmax + 1, int(fmax - fmin) / 10))
        ax.set_yticklabels(freq_series)

        ax.set_xlabel(' Time (s)', fontdict=font)
        ax.set_ylabel('Frequency (Hz)', fontdict=font)
        plt.title(title + ' (' + class1label + '/' + class2label + ') Sensor ' + electrodes[idx], fontdict=font)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('ERD/ERS', rotation=270, labelpad=15)
        plt.show()

    # Plot compared metric for 2 classes using Visualization_Data functions
    def btnMetric(self, features, metricLabel, isLog, title):
        if checkFreqsMinMax(self.userFmin, self.userFmax, self.samplingFreq):
            electrodeExists = False
            electrodeIdx = 0
            electrodeToDisp = self.electrodePsd.text()
            for idx, elec in enumerate(features.electrodes_final):
                if elec == electrodeToDisp:
                    electrodeIdx = idx
                    electrodeExists = True
                    break

            if not electrodeExists:
                myMsgBox("No sensor with this name found")
            else:                
                fmin = self.userFmin
                fmax = self.userFmax
                class1 = self.parameterDict["AcquisitionParams"]["Class1"]
                class2 = self.parameterDict["AcquisitionParams"]["Class2"]
                each_point = 1
                fig = plot_comparison_plotly(
                    features.power_cond1, features.power_cond2,
                    features.Rsquare, features.freqs_array,
                    electrodeIdx, features.electrodes_final,
                    each_point, fmin, fmax, features.fres, class1, class2,
                    metricLabel, isLog, title)

                filename = str(self.workspaceFolder + "/lastfigure.html")
                plotly.offline.plot(fig, filename=filename, auto_open=True)

    # Plot "Brain topography", using either Power Spectrum (in same pipeline)
    # or Node Strength (or similar metric) (in Connectivity pipeline)
    def btnTopo(self, features, title):
        error = True

        tempR2 = features.Rsquare.copy()
        # if "consider the sign" is checked,
        # modify the R2 to display
        useSign = self.autofeatUseSignComboBox.currentIndex()
        if useSign > 0:
            tempRsign = features.Rsign_tab.copy()
            if useSign == 2:
                # reverse the sign for the Rsquare map...
                tempRsign[np.where(features.Rsign_tab < 0)] = 1
                tempRsign[np.where(features.Rsign_tab > 0)] = -1
            tempR2 = tempR2 * tempRsign

        # 2 cases : 1 freq bin, or freq range
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.samplingFreq / 2):
            print("Freq Topo: " + self.freqTopo.text())
            error = False
            freqMax = -1
            topo_plot(tempR2, title, self.sensorMontage, self.customMontagePath,
                      features.electrodes_final, int(self.freqTopo.text()), freqMax,
                      features.fres, self.samplingFreq, self.colormapScale.isChecked(),
                      (useSign > 0) )
            plt.show()
        elif ":" in self.freqTopo.text() \
                and len(self.freqTopo.text().split(":")) == 2:
                    if self.freqTopo.text().split(":")[0].isdigit() \
                            and self.freqTopo.text().split(":")[1].isdigit():
                        freqMin = int(self.freqTopo.text().split(":")[0])
                        freqMax = int(self.freqTopo.text().split(":")[1])
                        if 0 < freqMin < freqMax < (self.samplingFreq / 2):
                            error = False
                            topo_plot(tempR2, title, self.sensorMontage, self.customMontagePath,
                                      features.electrodes_final, int(self.freqTopo.text()), freqMax,
                                      features.fres, self.samplingFreq, self.colormapScale.isChecked(),
                                      (useSign > 0))
                            plt.show()

        if error:
            myMsgBox("Invalid frequency for topography")

    def btnConnectSpect(self, features, title):
        qt_plot_connectSpectrum(features.connect_cond1, features.connect_cond2,
                                self.userChan1.text(), self.userChan2.text(), features.electrodes_orig, features.fres,
                                self.parameterDict["AcquisitionParams"]["Class1"], self.parameterDict["AcquisitionParams"]["Class2"], title)

    def btnConnectMatrices(self, features, title):
        if 0 < self.userFmin < (self.samplingFreq / 2) \
                and  0 < self.userFmax < (self.samplingFreq / 2):
            print("Freq connectivity matrices: " + str(self.userFmin) + " to " + str(self.userFmax) )
        else:
            myMsgBox("Error in frequency used for displaying connectivity matrices...")
            return

        qt_plot_connectMatrices(features.connect_cond1, features.connect_cond2,
                                self.userFmin, self.userFmax,
                                features.electrodes_orig,
                                self.parameterDict["AcquisitionParams"]["Class1"],
                                self.parameterDict["AcquisitionParams"]["Class2"], title)

    def btnConnectome(self, features, title):
        if self.percentStrong.text().isdigit() \
                and 0 < int(self.percentStrong.text()) <= 100:
            print("Percentage of strongest links: " + self.percentStrong.text() + "%")
        else:
            myMsgBox("Error in percentage used for displaying strongest links...")
            return

        if 0 < self.userFmin < (self.samplingFreq / 2) \
                and 0 < self.userFmax < (self.samplingFreq / 2):
            print("Freq connectivity matrices: " + str(self.userFmin) + " to " + str(self.userFmax) )
        else:
            myMsgBox("Error in frequency used for displaying connectivity matrices...")
            return

        qt_plot_strongestConnectome(features.connect_cond1, features.connect_cond2,
                                    int(self.percentStrong.text()),
                                    self.userFmin, self.userFmax,
                                    features.electrodes_orig,
                                    self.parameterDict["AcquisitionParams"]["Class1"],
                                    self.parameterDict["AcquisitionParams"]["Class2"], title)

    def btnAddPair(self, selectedFeats, layout, featText):
        if len(selectedFeats) == 0:
            # Remove "no feature" label
            item = layout.itemAt(3)
            if item:  # check if it exists. It may have been already deleted!
                widget = item.widget()
                widget.deleteLater()

        if not featText:
        # default text
            featText = "CP3;8"

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
        setKeyValue(self.workspaceFile, "ovDesignerPath", self.parameterDict["ovDesignerPath"])
        return

    def toggleAdvanced(self):
        # Toggles some options in the interface...

        # Toggle "advanced" status
        self.advanced = not self.advanced

        self.labelRunClassif.setVisible(self.advanced)
        self.btn_selectFilesClassif.setVisible(self.advanced)
        self.btn_runClassif.setVisible(self.advanced)
        self.fileListWidgetClassifRun.setVisible(self.advanced)

        if self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.enableSpeedUp.setVisible(self.advanced)
            self.speedUpLabel.setVisible(self.advanced)

        return

    def vizSetFreqMin(self):
        text, ok = QInputDialog.getText(self, 'Min frequency for general R2 map and Metric comparison',
                                        'Enter a number between 0 and (sampFreq/2)', text=str(self.userFmin))
        if ok:
            # Check if it's all numeric
            for c in text:
                if not c.isnumeric():
                    myMsgBox("Please enter a number")
                    return

            if text == "":
                myMsgBox("Please enter a number")
                return

            self.userFmin = int(text)

        return

    def vizSetFreqMax(self):
        text, ok = QInputDialog.getText(self, 'Max frequency for general R2 map and Metric comparison',
                                        'Enter a number between 0 and (sampFreq/2)', text=str(self.userFmax))
        if ok:
            # Check if it's all numeric
            for c in text:
                if not c.isnumeric():
                    myMsgBox("Please enter a number")
                    return

            if text == "":
                myMsgBox("Please enter a number")
                return

            self.userFmax = int(text)

        return

    def extractionSetStimulations(self):
        # ----------
        # Allow user to set Stimulations corresponding to classes
        # ----------
        text, ok = QInputDialog.getText(self, 'Class Stimulation names for extraction',
                                        'Enter two strings separated with \";\"', text=self.extractionStims)
        if ok:
            # Check if it's all alphanumeric, except for ":"...
            for c in text:
                if not c.isalnum():
                    if c != ";" and c != "_":  # we authorize "_" for openvibe...
                        myMsgBox("Please respect formatting: two strings separated with \";\"")
                        return

            if text == "":
                myMsgBox("Please respect formatting: two strings separated with \";\"")
                return

            stims = text.split(";")
            if len(stims) != 2:
                myMsgBox("Please respect formatting: two numbers separated with \";\"")
                return

            self.extractionStims = text
            # Save in workspace file
            setKeyValue(self.workspaceFile, "extractionStims", self.extractionStims)
            self.parameterDict["extractionStims"] = self.extractionStims
        return

    def btnAutoFeat(self, results1, results2):

        # Automatic feature selection : find best R² among
        # predetermined list of channels and in range of frequencies

        # Note: if dual mode, we assume the sampling freq,
        # list of electrodes, etc. are the same for PSD & NS cases

        if not results1 and not results2:
            myMsgBox("What are you doing???")
            return

        results1.autoselected = None
        results2.autoselected = None
        freqsArray = None

        if results1:
            freqsArray = results1.freqs_array
        elif results2:
            freqsArray = results2.freqs_array

        # Get Freq and Channel range from the interface
        # If Freq range &/or Channel list are empty, use full range
        if self.autoFeatFreqRange == "":
            if results1:
                self.autoFeatFreqRange = "1:" + str(int(results1.samplingFreq/2+1))
            else:
                self.autoFeatFreqRange = "1:" + str(int(results2.samplingFreq/2+1))
        if self.autoFeatChannelList == []:
            if results1:
                self.autoFeatChannelList = results1.electrodes_final
            else:
                self.autoFeatChannelList = results2.electrodes_final

        print("AutoFeat: Sublist of channels: " + str(self.autoFeatChannelList))
        print("AutoFeat: Frequency range: " + str(self.autoFeatFreqRange))
        print("AutoFeat: Frequency resolution: " + str(results1.fres))

        # Get indices corresponding to the selected channel names
        # TODO : allow for case-insensitive selection (e.g. FCz == Fcz)
        Index_electrode = []
        for chan in self.autoFeatChannelList:
            try:
                idx = results1.electrodes_final.index(chan)
            except ValueError:
                myMsgBox("AutoFeat: Electrode " + chan + " not in electrode list of selected files")
                return
            Index_electrode.append(idx)
        print("Index_electrode:  " + str(Index_electrode))

        # Check if frequencies are correct...
        freqMin = int(self.autoFeatFreqRange.split(":")[0])
        freqMax = int(self.autoFeatFreqRange.split(":")[1])
        if freqMax <= freqMin or freqMax > self.samplingFreq / 2 or freqMin < 0 or freqMax < 1:
            myMsgBox("AutoFeat: Invalid frequency range ( freqmin:freqmax )" )
            return

        # find closest indices in the frequencies list, corresponding to fmin and fmax
        valueFreqmin, idxFreqmin = find_nearest(freqsArray, freqMin)
        valueFreqmax, idxFreqmax = find_nearest(freqsArray, freqMax)

        # Loop and find best features in the R² sub-map
        for result in [results1, results2]:
            if len(result.Rsquare) > 0:
                result.autoselected = []
                Rsquare_reduced = result.Rsquare[Index_electrode, idxFreqmin:idxFreqmax]

                # if "Use the sign" is checked
                # we apply the sign map to Rsquare
                # ==> R² values corresponding to Class1 < Class2 will be negative and won't count
                # for the search of max values
                useSign = self.autofeatUseSignComboBox.currentIndex()
                if useSign > 0:
                    tempRsign = result.Rsign_tab.copy()
                    if useSign == 2:
                        # reverse the sign for the Rsquare map...
                        tempRsign[np.where(result.Rsign_tab < 0)] = 1
                        tempRsign[np.where(result.Rsign_tab > 0)] = -1
                    Rsign_reduced = tempRsign[Index_electrode, idxFreqmin:idxFreqmax]
                    Rsquare_reduced = Rsquare_reduced * Rsign_reduced

                Max_per_electrode = Rsquare_reduced.max(1)
                indices_max = list(reversed(np.argsort(Max_per_electrode)))[0:3]  # indices of 3 max values within the scope of Index_electrodes
                indices_max_final = [Index_electrode[i] for i in indices_max]

                for idx in indices_max_final:
                    r2Vals = result.Rsquare[idx, idxFreqmin:idxFreqmax]
                    idxMaxValue = idxFreqmin + np.argmax(r2Vals)
                    # The selected frequency is in "index" mode, we need to translate it to a human-readable format
                    result.autoselected.append((result.electrodes_final[idx], int(freqsArray[idxMaxValue])))

                if len(result.autoselected) < 1:
                    myMsgBox("AutoFeat: Error in automatic selection of best features")
                    # Todo: make more secure & explicit
                    return
                print("Best feats: " + str(result.autoselected))

        # Remove all pairs of features in columns
        # TODO : refactor. A bit dirty...
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # Remove "no feature" label
            if len(self.selectedFeats[0]) == 0:
                item = self.qvFeatureLayouts[0].itemAt(2)
                if item:
                    widget = item.widget()
                    if widget.text() == "No feature":
                        widget.deleteLater()
        # Remove all existing features
        while len(self.selectedFeats[0]) > 0:
            result = self.qvFeatureLayouts[0].getWidgetPosition(self.selectedFeats[0][-1])
            self.qvFeatureLayouts[0].removeRow(result[0])
            self.selectedFeats[0].pop()

        # Same, in case with two feature/metric types...
        if self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            # Remove "no feature" label
            if len(self.selectedFeats[0]) == 0:
                item = self.qvFeatureLayouts[0].itemAt(3)
                if item:
                    widget = item.widget()
                    if widget.text() == "No feature":
                        widget.deleteLater()
            # Remove all existing features
            while len(self.selectedFeats[0]) > 0:
                result = self.qvFeatureLayouts[0].getWidgetPosition(self.selectedFeats[0][-1])
                self.qvFeatureLayouts[0].removeRow(result[0])
                self.selectedFeats[0].pop()

            # Remove "no feature" label in second column
            if len(self.selectedFeats[1]) == 0:
                item = self.qvFeatureLayouts[1].itemAt(3)
                if item:
                    widget = item.widget()
                    if widget.text() == "No feature":
                        widget.deleteLater()
            # Remove all features in second column
            while len(self.selectedFeats[1]) > 0:
                result = self.qvFeatureLayouts[1].getWidgetPosition(self.selectedFeats[1][-1])
                self.qvFeatureLayouts[1].removeRow(result[0])
                self.selectedFeats[1].pop()

        # get auto-selected features and add them to the interface
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            for featPair in results1.autoselected:
                featText = str(featPair[0]) + ';' + str(featPair[1])
                self.btnAddPair(self.selectedFeats[0], self.qvFeatureLayouts[0], featText)

        # Special cases for pipelines 3&4 (dual features)
        if self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4] :
            for featPair in results1.autoselected:
                featText = str(featPair[0]) + ';' + str(featPair[1])
                self.btnAddPair(self.selectedFeats[0], self.qvFeatureLayouts[0], featText)
            for featPair in results2.autoselected:
                featText = str(featPair[0]) + ';' + str(featPair[1])
                self.btnAddPair(self.selectedFeats[1], self.qvFeatureLayouts[1], featText)

    def autoFeatSetChannelSubselection(self):
        # ----------
        # Allow user to select a list of channels in which the "automatic selection of feature"
        # can take place
        # ----------
        displayed = ";".join(self.autoFeatChannelList)
        text, ok = QInputDialog.getText(self, 'Channel list for automatic feature selection', 'Enter a list of channels separated with \";\"', text=displayed)

        if ok:
            # Check if it's all alphanumeric, except for ";"
            # another exception : dots ("."), as it's used in physionet dataset...
            for c in text:
                if not c.isalnum():
                    if c != ";" and c != ".":
                        myMsgBox("Please respect formatting: channels as alphanumeric characters (or dots), separated with \";\"")
                        return
            if text == "":
                self.autoFeatChannelList = []
                return

            self.autoFeatChannelList = text.split(";")
            # Save in workspace file
            setKeyValue(self.workspaceFile, "autoFeatChannelList", self.autoFeatChannelList)
            self.parameterDict["autoFeatChannelList"] = self.autoFeatChannelList

        return

    def autoFeatSetFreqRange(self):
        # ----------
        # Allow user to select a range of frequencies in which the "automatic selection of feature"
        # can take place
        # ----------
        text, ok = QInputDialog.getText(self, 'Frequency range for automatic feature selection', 'Enter two numbers separated with \":\"', text=self.autoFeatFreqRange)
        if ok:
            # Check if it's all alphanumeric, except for ":"...
            for c in text:
                if not c.isalnum():
                    if c != ":":
                        myMsgBox("Please respect formatting: two numbers separated with \":\"")
                        return

            if text == "":
                self.autoFeatFreqRange = ""
                return

            range = text.split(":")
            if len(range) != 2:
                myMsgBox("Please respect formatting: two numbers separated with \":\"")
                return

            self.autoFeatFreqRange = text
            # Save in workspace file
            setKeyValue(self.workspaceFile, "autoFeatFreqRange", self.autoFeatFreqRange)
            self.parameterDict["autoFeatFreqRange"] = self.autoFeatFreqRange
        return

    def checkExistenceExtractFiles(self, file):
        extractFolder = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "extract")
        if not os.path.exists(extractFolder):
            return False

        class1 = self.parameterDict["AcquisitionParams"]["Class1"]
        class2 = self.parameterDict["AcquisitionParams"]["Class2"]
        if self.parameterDict["pipelineType"] == settings.optionKeys[1] \
            or self.parameterDict["pipelineType"] == settings.optionKeys[3] \
            or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            # PSD
            metric = "SPECTRUM"
            extractFile1 = str(os.path.splitext(file)[0] + "-" + metric + "-" + class1 + ".csv")
            extractFile2 = str(os.path.splitext(file)[0] + "-" + metric + "-" + class2 + ".csv")
            extractFile1Path = os.path.join(extractFolder, extractFile1)
            extractFile2Path = os.path.join(extractFolder, extractFile2)
            if not os.path.exists(extractFile1Path) or not os.path.exists(extractFile2Path):
                return False

        if self.parameterDict["pipelineType"] == settings.optionKeys[2] \
            or self.parameterDict["pipelineType"] == settings.optionKeys[3]\
            or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            # CONNECT
            metric = "CONNECT"
            extractFile1 = str(os.path.splitext(file)[0] + "-" + metric + "-" + class1 + ".csv")
            extractFile2 = str(os.path.splitext(file)[0] + "-" + metric + "-" + class2 + ".csv")
            extractFile1Path = os.path.join(extractFolder, extractFile1)
            extractFile2Path = os.path.join(extractFolder, extractFile1)
            if not os.path.exists(extractFile1Path) or not os.path.exists(extractFile2Path):
                return False

        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            trainFolder = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train")
            if not os.path.exists(trainFolder):
                return False
            trialsFile = os.path.join(trainFolder, str(os.path.splitext(file)[0] + "-TRIALS.csv"))
            if not os.path.exists(trialsFile):
                return False

            signalsFolder = os.path.join(self.workspaceFolder, "signals")
            metaFile = os.path.join(signalsFolder, str(os.path.splitext(file)[0] + "-META.csv"))
            if not os.path.exists(metaFile):
                return False

        return True

    def updateTrainingAttemptsTree(self):
        # Update training results from config file
        self.lastTrainingResults.clear()
        resultsDict = getTrainingResults(self.workspaceFile, self.currentSessionId)
        attempts = []
        if resultsDict:
            for attemptId in resultsDict.keys():
                attempts.append(attemptId)
                attemptItem = QTreeWidgetItem(self.lastTrainingResults)
                attemptItem.setFlags(attemptItem.flags() | Qt.ItemIsSelectable)
                attemptItem.setText(0, attemptId)
                attemptItem.setText(1, resultsDict[attemptId]["Score"])
                firstFeatWritten = False
                for metricType in resultsDict[attemptId]["Features"]:
                    for featPair in resultsDict[attemptId]["Features"][metricType]:
                        featItem = QTreeWidgetItem(None)
                        tempString = str(metricType + " " + featPair)
                        featItem.setText(2, tempString)
                        featItem.setFlags(featItem.flags() & ~Qt.ItemIsSelectable)
                        attemptItem.addChild(featItem)
                        # add first feat to parent row, then user will need to
                        # expand row to see more...
                        if not firstFeatWritten:
                            dispFeat = featPair
                            if len(resultsDict[attemptId]["Features"][metricType]) > 1:
                                dispFeat += str(" + others...")
                            attemptItem.setText(2, dispFeat)
                            firstFeatWritten = True
                for file in resultsDict[attemptId]["SignalFiles"]:
                    fileItem = QTreeWidgetItem(None)
                    fileItem.setText(2, file)
                    fileItem.setFlags(fileItem.flags() & ~Qt.ItemIsSelectable)
                    attemptItem.addChild(fileItem)

        # collapse all items
        self.lastTrainingResults.collapseAll()

    def btnSelectFilesClassif(self):
        # Open file browser to select files upon which we want to apply the selected classifier
        # + update the indicative list
        self.fileListWidgetClassifRun.clear()
        directory = os.getcwd()
        paths, dummy = QFileDialog.getOpenFileNames(self, "Signal files", str(directory))

        for path in paths:
            if not ".ov" in path:
                myMsgBox("Warning:\n" + path + "\ndoesn't seem to be a valid signal file")
            else:
                item = QTreeWidgetItem(self.fileListWidgetClassifRun)
                item.setText(0, os.path.basename(path) )
                fullpath = QTreeWidgetItem(None)
                fullpath.setText(0, path)
                item.addChild(fullpath)

    def getTrainingParamsFromSelectedAttempt(self):

        selectedAttempt = self.lastTrainingResults.selectedItems()

        if not selectedAttempt:
            myMsgBox("Please select one training attemp in the list above")
            return

        baseNode = selectedAttempt[0]
        classifIdx = baseNode.text(0)
        nbChildren = baseNode.childCount()
        pipelineTextToFind = ""
        pipelineTextToFind2 = ""
        listFeat = []
        listFeat2 = []
        sampFreq = None
        electrodeList = None
        paramsFound = False

        # which metric str to look for in the column text
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            pipelineTextToFind = settings.optionKeys[1]
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            pipelineTextToFind = settings.optionKeys[2]
        elif self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
            pipelineTextToFind = settings.optionKeys[1]
            pipelineTextToFind2 = settings.optionKeys[2]

        # iterate over all sub-lines of selected line, in results list widget
        for child in range(0, nbChildren):
            textInfo = baseNode.child(child).text(2)  # relevant info in column 2. Might change later...

            if pipelineTextToFind in textInfo:
                textInfo = textInfo.removeprefix(str(pipelineTextToFind + " "))
                listFeat.append(textInfo)

            # special case: "Mixed" pipeline: 2 lists to extract
            if self.parameterDict["pipelineType"] == settings.optionKeys[3] \
                    or self.parameterDict["pipelineType"] == settings.optionKeys[4]:
                if pipelineTextToFind2 in textInfo:
                    textInfo = textInfo.removeprefix(str(pipelineTextToFind2 + " "))
                    listFeat2.append(textInfo)

            if not paramsFound:
                if "-TRIALS.csv" in textInfo:
                    sampFreq, electrodeList = extractMetadata(
                        os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", textInfo))
                    if sampFreq and electrodeList:
                        paramsFound = True

        return classifIdx, listFeat, listFeat2, sampFreq, electrodeList

    def btnUseSelectedClassif(self):
        # ----------
        # Update "online" (sc3) scenario with "classifier-weights" file from selected
        # training attempt in the list of attempts&results.
        # ----------

        # === 1st step : Get selected training attempt's ID and parameters (features)
        classifIdx, listFeat, listFeat2, sampFreq, electrodeList = self.getTrainingParamsFromSelectedAttempt()

        print("classifIdx : " + str(classifIdx))
        print("listFeat : " + str(listFeat))
        print("listFeat2 : " + str(listFeat2))
        print("sampFreq : " + str(sampFreq))
        print("electrodeList: " + str(electrodeList))

        # === 2nd step : check if classifier-weights-X.xml exists
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            classifWeightsPath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train",
                                              str("classifier-weights-" + str(classifIdx) + ".xml"))
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            classifWeightsPath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train",
                                              str("classifier-weights-" + str(classifIdx) + ".pkl"))

        if not os.path.exists(classifWeightsPath):
            myMsgBox("ERROR: for selected classification results (" + str(
                classifIdx) + "),\nweights file not found in workspace.")
            return

        # Reformat to openvibe's preference... C:/etc.
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0] and platform.system() == 'Windows':
            classifWeightsPath = classifWeightsPath.replace("\\", "/")

        # === 3rd step : update sc3-online.xml with classifier-weights file and relevant features
        trainingParamDict = self.parameterDict.copy()
        shouldRun = False
        isOnline = True
        templateFolder = settings.optionsTemplatesDir[self.parameterDict["pipelineType"]]

        # Instantiate the thread...
        if self.parameterDict["bciPlatform"] == settings.availablePlatforms[0]:  # openvibe
            self.runClassThread = RunClassifier([], templateFolder,
                                                self.workspaceFolder, self.ovScript,
                                                classifWeightsPath, listFeat, listFeat2,
                                                trainingParamDict, sampFreq, electrodeList,
                                                shouldRun, isOnline)
        elif self.parameterDict["bciPlatform"] == settings.availablePlatforms[1]:  # timeflux
            scenfile= os.path.join(self.workspaceFolder, settings.templateScenFilenames_timeflux[2])

            self.runClassThread = UseClassifier_Timeflux(scenfile, self.workspaceFolder, self.parameterDict,
                                                         self.currentSessionId, listFeat, classifWeightsPath)

        # Signal: Running work thread finished
        self.runClassThread.over.connect(self.running_over)

        # Launch the work thread
        self.runClassThread.start()

        self.runTimerStart = time.perf_counter()
        self.progressBarRun = None

        return

    def btnRunClassif(self):
        # ------
        # Run the selected classifier on the selected files.
        # ------

        # - check if files have been selected (browse...)
        # - get the selected classifier = line in the results list
        #   => check if a line is selected, extract its index X and feature parameters
        # - check if associated classifier-weights-X.xml exists
        # - update template scenario with feature(s) + weight xml file
        # - run the scenario and get score

        # === 1st step: check if signal files have been selected by browsing (= not empty list)
        if self.fileListWidgetClassifRun.topLevelItemCount() == 0:
            myMsgBox("Please use the \"Browse\" button to select signal file(s).")
            return

        # create list of files...
        self.classifFiles = []
        for i in range(0, self.fileListWidgetClassifRun.topLevelItemCount()):
            self.classifFiles.append(self.fileListWidgetClassifRun.topLevelItem(i).child(0).text(0))

        # === 2nd step : get line idx (& parameters) in classification results list
        classifIdx, listFeat, listFeat2, sampFreq, electrodeList = \
            self.getTrainingParamsFromSelectedAttempt()

        print("classifIdx : " + str(classifIdx))
        print("listFeat : " + str(listFeat))
        print("listFeat2 : " + str(listFeat2))

        print("list of files: " + str(self.classifFiles))
        print("sampFreq : " + str(sampFreq))
        print("electrodeList: " + str(electrodeList))

        # === 3rd step : check if classifier-weights-X.xml exists
        classifWeightsPath = os.path.join(self.workspaceFolder, "sessions", self.currentSessionId, "train", str("classifier-weights-"+str(classifIdx)+".xml"))
        if not os.path.exists(classifWeightsPath):
            myMsgBox("ERROR: for selected classification results (" + str(classifIdx) + "),\nweights file not found in workspace.")
            return
        # Reformat to openvibe's preference... C:/etc.
        if platform.system() == 'Windows':
            classifWeightsPath = classifWeightsPath.replace("\\", "/")

        # === 4th step : run scenario thread

        self.enableExtractionGui(False)
        self.enableTrainGui(False)
        trainingParamDict = self.parameterDict.copy()

        # create progress bar window...
        self.progressBarRun = ProgressBar("Running classification", "File...", len(self.classifFiles))

        # Instantiate the thread...
        shouldRun = True
        isOnline = False
        templateFolder = settings.optionsTemplatesDir[self.parameterDict["pipelineType"]]
        self.runClassThread = RunClassifier(self.classifFiles, templateFolder,
                                                self.workspaceFolder, self.ovScript,
                                                classifWeightsPath,
                                                listFeat, listFeat2,
                                                trainingParamDict, sampFreq, electrodeList,
                                                shouldRun, isOnline)

        # Signal: RunClassif work thread finished one step
        # Increment progress bar + change its label
        self.runClassThread.info.connect(self.progressBarRun.increment)
        self.runClassThread.info2.connect(self.progressBarRun.changeLabel)
        # Signal: RunClassif work thread finished
        self.runClassThread.over.connect(self.running_over)
        # Launch the work thread
        self.runClassThread.start()

        self.runTimerStart = time.perf_counter()

        return

    def running_over(self, success, resultsText):
        # Running work thread is over, so we kill the progress bar,
        # display a msg with results, and make the running Gui available again
        self.runTimerEnd = time.perf_counter()
        elapsed = self.runTimerEnd - self.runTimerStart
        print("=== Running done in: ", str(elapsed))

        if self.progressBarRun:
            self.progressBarRun.finish()

        if success:
            textDisplayed = str(resultsText)
            msg = QMessageBox()
            msg.setText(textDisplayed)

            msg.setStyleSheet("QLabel{min-width: 1200px;}")
            msg.setWindowTitle("Classification Score")
            msg.exec()
        else:
            myMsgBox(resultsText)

        self.enableGui(True)

# ------------------------------------------------------
# STATIC FUNCTIONS
# ------------------------------------------------------
def checkFreqsMinMax(fmin, fmax, fs):
    ok = True
    if fmin < 0 or fmax < 0:
        ok = False
    elif fmin > (fs/2)+1 or fmax > (fs/2)+1:
        ok = False
    elif fmin >= fmax:
        ok = False

    if not ok:
        errorStr = str("fMin and fMax should be numbers between 0 and " + str(fs / 2 + 1))
        errorStr = str(errorStr + "\n and fMin < fMax")
        myMsgBox(errorStr)

    return ok

# Plot "connectivity spectrum" from a RAW connectivity matrix.
# TODO: REMOVE? UNUSED!
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

# Plot full RAW connectivity matrix for a given [fmin;fmax] range.
# TODO: REMOVE? UNUSED!
def qt_plot_connectMatrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label, title):
    plot_connect_matrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label, title)
    plt.show()

# Plot % of strongest nodes, from a RAW connectivity matrix, in range [fmin;fmax].
# TODO: REMOVE? UNUSED!
def qt_plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label, title):
    plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label, title)
    plt.show()

# main entry point...
def launch(folder, fullWorkspacePath):
    if not QApplication.instance():
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

    # Check that workspace file exists, is a json file, and contains HappyFeatVersion field...
    if not os.path.exists(fullWorkspacePath):
        print("\tError: can't open workspace file.")
        print("\tPlease check that you provided the full path to your .hfw file")
        print("\t(use happyfeat_welcome to initialize new workspaces)")
        return -1
    with open(fullWorkspacePath, "r") as wp:
        workDict = json.load(wp)
        if not "HappyFeatVersion" in workDict:
            print("\tError: invalid workspace file.")
            # TODO: more checks...
            return -1

    dlg = Dialog(fullWorkspacePath)
    retVal = dlg.exec()

    app.shutdown()

    return retVal


if __name__ == '__main__':
    # Check that a workspace file has been provided
    if len(sys.argv) == 1:
        print("\tError: missing argument.\n\tPlease call this interface with a workspace file (.hfw).")
        print("\tEx: python 2-featureExtractionInterface <fullpath>/myworkspace.hfw")
        print("\t(use happyfeat_welcome to initialize new workspaces)")
        sys.exit(-1)

    elif len(sys.argv) == 2:
        retVal = launch(sys.argv[0], sys.argv[1])

    print("Exit thread")
    sys.exit(retVal)
