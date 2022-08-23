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

        # -----------------------------------
        self.dataNp1 = []
        self.dataNp2 = []
        self.dataNp1baseline = []
        self.dataNp2baseline = []
        self.Features = Features()
        self.progressBar = None

        self.extractThread = None
        self.loadFilesForVizThread = None
        self.trainClassThread = None

        self.plotBtnsEnabled = False

        # Sampling Freq: to be loaded later, in CSV files
        self.samplingFreq = None

        # GET PARAMS FROM JSON FILE
        self.scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        if "params.json" in os.listdir(os.path.join(self.scriptPath, "generated")):
            print("--- Using parameters from params.json...")
            self.jsonfullpath = os.path.join(self.scriptPath, "generated", "params.json")
            with open(self.jsonfullpath) as jsonfile:
                self.parameterDict = json.load(jsonfile)
            self.ovScript = self.parameterDict["ovDesignerPath"]
        else:
            # WARN create a params.json with default parameters
            myMsgBox("--- WARNING : no params.json found, please use 1-bcipipeline_qt.py first !")
            self.reject()

        # -----------------------------------------------------------------------
        # CREATE INTERFACE...
        # dlgLayout : Entire Window, separated in horizontal panels
        # Left-most: layoutExtract (for running sc2-extract)
        # Center: Visualization
        # Right-most: Feature Selection & classifier training
        #self.setWindowTitle('goodViBEs - Feature Selection interface')
        self.setWindowTitle('Feature Selection interface')
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
        # AND RUNNING SCENARIO FOR DATA EXTRACTION
        labelSignal = str("===== FEATURE EXTRACTION FROM SIGNAL FILES =====")
        self.labelSignal = QLabel(labelSignal)
        self.labelSignal.setAlignment(QtCore.Qt.AlignCenter)

        self.fileListWidget = QListWidget()
        self.fileListWidget.setSelectionMode(QListWidget.MultiSelection)

        # Label + *editable* list of parameters
        labelExtractParams = str("--- Extraction parameters ---")
        self.labelExtractParams = QLabel(labelExtractParams)
        self.labelExtractParams.setAlignment(QtCore.Qt.AlignCenter)

        self.extractParamsDict = self.getExtractionParameters()
        extractParametersLayout = QHBoxLayout()
        self.layoutExtractLabels = QVBoxLayout()
        self.layoutExtractLineEdits = QVBoxLayout()
        extractParametersLayout.addLayout(self.layoutExtractLabels)
        extractParametersLayout.addLayout(self.layoutExtractLineEdits)

        for idx, (paramId, paramVal) in enumerate(self.extractParamsDict.items()):
            labelTemp = QLabel()
            labelTemp.setText(settings.paramIdText[paramId])
            self.layoutExtractLabels.addWidget(labelTemp)
            lineEditExtractTemp = QLineEdit()
            lineEditExtractTemp.setText(self.parameterDict[paramId])
            self.layoutExtractLineEdits.addWidget(lineEditExtractTemp)

        # Label + un-editable list of parameters for reminder
        labelReminder = str("--- Experiment parameters (set in Generator GUI) ---")
        self.labelReminder = QLabel(labelReminder)
        self.labelReminder.setAlignment(QtCore.Qt.AlignCenter)

        self.expParamListWidget = QListWidget()
        self.expParamListWidget.setEnabled(False)
        self.experimentParamsDict = self.getExperimentalParameters()
        minHeight = 0
        for idx, (paramId, paramVal) in enumerate(self.experimentParamsDict.items()):
            self.expParamListWidget.addItem(settings.paramIdText[paramId] + ": \t" + str(paramVal))
            minHeight += 30

        self.expParamListWidget.setMinimumHeight(minHeight)

        # Extraction button
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

        self.formLayoutViz = QFormLayout()

        # LIST OF AVAILABLE ANALYSIS FILES WITH CURRENT CLASS
        self.availableFilesForVizList = QListWidget()
        self.availableFilesForVizList.setSelectionMode(QListWidget.MultiSelection)
        self.layoutViz.addWidget(self.availableFilesForVizList)

        # LIST OF PARAMETERS FOR VISUALIZATION
        # TODO : make it more flexible...
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
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
            self.electrodePsd.setText('C3')
            self.formLayoutViz.addRow('Sensor for PSD visualization', self.electrodePsd)
            # Param : Frequency to use for Topography
            self.freqTopo = QLineEdit()
            self.freqTopo.setText('12')
            self.formLayoutViz.addRow('Frequency for Topography (Hz)', self.freqTopo)

        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # Param : fmin for frequency based viz
            self.userFmin = QLineEdit()
            self.userFmin.setText('0')
            self.formLayoutViz.addRow('Frequency min', self.userFmin)
            # Param : fmax for frequency based viz
            self.userFmax = QLineEdit()
            self.userFmax.setText('40')
            self.formLayoutViz.addRow('Frequency max', self.userFmax)
            # Param : Electrode to use for Node Strength display
            self.electrodePsd = QLineEdit()
            self.electrodePsd.setText('C3')
            self.formLayoutViz.addRow('Sensor for Node Strength viz', self.electrodePsd)
            # Param : Frequency to use for Topography
            self.freqTopo = QLineEdit()
            self.freqTopo.setText('12')
            self.formLayoutViz.addRow('Frequency for Topography (Hz)', self.freqTopo)

        self.layoutViz.addLayout(self.formLayoutViz)

        self.layoutVizButtons = QVBoxLayout()

        # TODO : make it more flexible...
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            # Viz options for "Spectral Power" pipeline...
            self.btn_loadFilesForViz = QPushButton("Load spectrum file(s) for analysis")
            self.btn_r2map = QPushButton("Display Frequency-channel R² map")
            self.btn_timefreq = QPushButton("Display Time-Frequency ERD/ERS analysis")
            self.btn_psd = QPushButton("Display PSD comparison between classes")
            self.btn_topo = QPushButton("Display Brain Topography")
            # self.btn_w2map = QPushButton("Plot Wilcoxon Map")
            # self.btn_psd_r2 = QPushButton("Plot PSD comparison between classes")
            self.btn_loadFilesForViz.clicked.connect(lambda: self.loadFilesForViz())
            self.btn_r2map.clicked.connect(lambda: self.btnR2())
            self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq())
            self.btn_psd.clicked.connect(lambda: self.btnPsd())
            self.btn_topo.clicked.connect(lambda: self.btnTopo())
            # self.btn_w2map.clicked.connect(lambda: self.btnW2())
            # self.btn_psd_r2.clicked.connect(lambda: self.btnpsdR2())

            self.layoutVizButtons.addWidget(self.btn_loadFilesForViz)
            self.layoutVizButtons.addWidget(self.btn_r2map)
            self.layoutVizButtons.addWidget(self.btn_psd)
            self.layoutVizButtons.addWidget(self.btn_timefreq)
            self.layoutVizButtons.addWidget(self.btn_topo)
            # self.layoutVizButtons.addWidget(self.btn_w2map)
            # self.layoutVizButtons.addWidget(self.btn_psd_r2)

        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # Viz options for "Connectivity" pipeline...
            self.btn_loadFilesForViz = QPushButton("Load connectivity file(s) for analysis")
            # self.btn_connectSpect = QPushButton("Display connectivity \"spectrum\" for given channel pair")
            # self.btn_connectMatrices = QPushButton("Display connectivity matrices for freq band")
            # self.btn_connectome = QPushButton("Display connectome using threshold & freq band")
            self.btn_r2map = QPushButton("Display Frequency-channel R² map (NODE STRENGTH)")
            self.btn_metric = QPushButton("Display NODE STRENGTH comparison between classes")
            self.btn_topo = QPushButton("Display NODE STRENGTH Brain Topography")

            self.btn_loadFilesForViz.clicked.connect(lambda: self.loadFilesForViz())
            # self.btn_connectSpect.clicked.connect(lambda: self.btnConnectSpect())
            # self.btn_connectMatrices.clicked.connect(lambda: self.btnConnectMatrices())
            # self.btn_connectome.clicked.connect(lambda: self.btnConnectome())
            self.btn_r2map.clicked.connect(lambda: self.btnR2())
            self.btn_metric.clicked.connect(lambda: self.btnMetric())
            self.btn_topo.clicked.connect(lambda: self.btnTopo())

            self.layoutVizButtons.addWidget(self.btn_loadFilesForViz)
            # self.layoutVizButtons.addWidget(self.btn_connectSpect)
            # self.layoutVizButtons.addWidget(self.btn_connectMatrices)
            # self.layoutVizButtons.addWidget(self.btn_connectome)
            self.layoutVizButtons.addWidget(self.btn_r2map)
            self.layoutVizButtons.addWidget(self.btn_metric)
            self.layoutVizButtons.addWidget(self.btn_topo)

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
        self.btn_selectFeatures = QPushButton("TRAIN CLASSIFIER")
        self.btn_allCombinations = QPushButton("FIND BEST COMBINATION")
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
        self.btn_loadFilesForViz.setEnabled(True)
        self.enablePlotBtns(False)

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
    def enablePlotBtns(self, myBool):
        # ----------
        # Update status of buttons used for plotting
        # ----------
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.btn_r2map.setEnabled(myBool)
            self.btn_timefreq.setEnabled(myBool)
            self.btn_psd.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)
            # self.btn_w2map.setEnabled(True)
            # self.btn_psd_r2.setEnabled(True)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            # self.btn_connectSpect.setEnabled(myBool)
            # self.btn_connectMatrices.setEnabled(myBool)
            # self.btn_connectome.setEnabled(myBool)
            self.btn_r2map.setEnabled(myBool)
            self.btn_metric.setEnabled(myBool)
            self.btn_topo.setEnabled(myBool)

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

        suffix = "-" + self.parameterDict["pipelineType"]
        workingFolder = os.path.join(signalFolder, "analysis")
        class1label = self.parameterDict["Class1"]
        class2label = self.parameterDict["Class2"]

        # first get a list of all csv files in workingfolder that match the condition
        availableCsvs = []
        for filename in os.listdir(workingFolder):
            if filename.endswith(str(suffix + "-" + class1label + ".csv")):
                basename = filename.removesuffix(str(suffix + "-" + class1label + ".csv"))
                otherClass = str(basename + suffix + "-" + class2label + ".csv")
                if otherClass in os.listdir(workingFolder):
                    availableCsvs.append(basename)

        # iterate over existing items in widget and delete those who don't exist anymore
        for x in range(self.availableFilesForVizList.count() - 1, -1, -1):
            tempitem = self.availableFilesForVizList.item(x).text()
            if tempitem.removesuffix(suffix) not in availableCsvs:
                self.availableFilesForVizList.takeItem(x)

        # iterate over filelist and add new files to listwidget
        # for that, create temp list of items in listwidget
        items = []
        for x in range(self.availableFilesForVizList.count()):
            items.append(self.availableFilesForVizList.item(x).text())
        for basename in availableCsvs:
            basenameSuffix = str(basename+suffix)
            if basenameSuffix not in items:
                self.availableFilesForVizList.addItem(basenameSuffix)

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

        # Retrieve param id from label...
        for idx in range(self.layoutExtractLabels.count()):
            paramLabel = self.layoutExtractLabels.itemAt(idx).widget().text()
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

        # create progress bar window...
        self.progressBar = ProgressBar("Extraction", len(self.fileListWidget.selectedItems()) )

        signalFiles = []
        for selectedItem in self.fileListWidget.selectedItems():
            signalFiles.append(selectedItem.text() )
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        scenFile = os.path.join(self.scriptPath, "generated", settings.templateScenFilenames[1])

        self.enableGui(False)

        self.extractThread = Extraction(self.ovScript, scenFile, signalFiles, signalFolder, self.parameterDict)
        self.extractThread.info.connect(self.progressBar.increment)
        self.extractThread.over.connect(self.extraction_over)
        self.extractThread.start()

    def extraction_over(self, success, text):
        self.progressBar.finish()
        if not success:
            myMsgBox(text)

        self.enableGui(True)

    def loadFilesForViz(self):
        # ----------
        # Load CSV files of selected extracted files for visualization
        # We need one CSV file per class, for simplicity...
        # ----------
        if not self.availableFilesForVizList.selectedItems():
            myMsgBox("Please select a set of files for analysis")
            return

        # create progress bar window...
        self.progressBar = ProgressBar("Loading Spectrum data", len(self.availableFilesForVizList.selectedItems()))

        analysisFiles = []
        for selectedItem in self.availableFilesForVizList.selectedItems():
            analysisFiles.append(selectedItem.text())
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")

        self.enableGui(False)

        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.loadFilesForVizThread = LoadFilesForVizPowSpectrum(analysisFiles, signalFolder, self.parameterDict, self.Features, self.samplingFreq)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.loadFilesForVizThread = LoadFilesForVizConnectivity(analysisFiles, signalFolder, self.parameterDict, self.Features, self.samplingFreq)

        self.loadFilesForVizThread.info.connect(self.progressBar.increment)
        self.loadFilesForVizThread.info2.connect(self.progressBar.changeLabel)
        self.loadFilesForVizThread.over.connect(self.loadFilesForViz_over)
        self.loadFilesForVizThread.start()

    def loadFilesForViz_over(self, success, text):
        self.progressBar.finish()
        if not success:
            myMsgBox(text)
            self.plotBtnsEnabled = False
        else:
            self.samplingFreq = self.Features.samplingFreq
            self.plotBtnsEnabled = True
        self.enableGui(True)

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

        # create progress bar window...
        self.progressBar = ProgressBar("Creating composite file", 2)

        trainingFiles = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            trainingFiles.append(selectedItem.text())
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        pipelineType = self.parameterDict["pipelineType"]
        templateFolder = os.path.join(self.scriptPath, settings.optionsTemplatesDir[pipelineType])
        scriptsFolder = self.scriptPath

        self.enableGui(False)

        self.trainClassThread = TrainClassifier(False, trainingFiles,
                                                signalFolder, templateFolder, scriptsFolder, self.ovScript,
                                                trainingSize, self.selectedFeats,
                                                self.parameterDict, self.samplingFreq)
        self.trainClassThread.info.connect(self.progressBar.increment)
        self.trainClassThread.info2.connect(self.progressBar.changeLabel)
        self.trainClassThread.over.connect(self.training_over)
        self.trainClassThread.start()

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

        # create progress bar window...
        i = []
        for item in self.fileListWidgetTrain.selectedItems():
            i.append("a")
        nbCombinations = len(list(myPowerset(i)))
        self.progressBar = ProgressBar("First combination", nbCombinations)

        trainingFiles = []
        for selectedItem in self.fileListWidgetTrain.selectedItems():
            trainingFiles.append(selectedItem.text())
        signalFolder = os.path.join(self.scriptPath, "generated", "signals")
        pipelineType = self.parameterDict["pipelineType"]
        templateFolder = os.path.join(self.scriptPath, settings.optionsTemplatesDir[pipelineType])
        scriptsFolder = self.scriptPath

        self.enableGui(False)

        self.trainClassThread = TrainClassifier(True, trainingFiles,
                                                signalFolder, templateFolder, scriptsFolder, self.ovScript,
                                                trainingSize, self.selectedFeats,
                                                self.parameterDict, self.samplingFreq)
        self.trainClassThread.info.connect(self.progressBar.increment)
        self.trainClassThread.info2.connect(self.progressBar.changeLabel)
        self.trainClassThread.over.connect(self.training_over)
        self.trainClassThread.start()

    def training_over(self, success, text):
        self.progressBar.finish()
        if success:
            msg = QMessageBox()
            msg.setText(text)
            msg.setStyleSheet("QLabel{min-width: 1200px;}")
            msg.setWindowTitle("Classifier Training Score")
            msg.exec_()
        else:
            myMsgBox(text)

        self.enableGui(True)

    def enableGui(self, myBool):
        # Extraction part...
        for idx in range(self.layoutExtractLabels.count()):
            self.layoutExtractLineEdits.itemAt(idx).widget().setEnabled(myBool)
        self.btn_runExtractionScenario.setEnabled(myBool)
        self.fileListWidget.setEnabled(myBool)
        self.btn_browseOvScript.setEnabled(myBool)

        # Viz part...
        self.btn_loadFilesForViz.setEnabled(myBool)
        self.availableFilesForVizList.setEnabled(myBool)

        # TODO : make better or more flexible...
        if self.parameterDict["pipelineType"] == settings.optionKeys[1]:
            self.userFmin.setEnabled(myBool)
            self.userFmax.setEnabled(myBool)
            self.electrodePsd.setEnabled(myBool)
            self.freqTopo.setEnabled(myBool)
        elif self.parameterDict["pipelineType"] == settings.optionKeys[2]:
            self.userFmin.setEnabled(myBool)
            self.userFmax.setEnabled(myBool)
            self.electrodePsd.setEnabled(myBool)
            self.freqTopo.setEnabled(myBool)

        self.btn_loadFilesForViz.setEnabled(myBool)
        if myBool and self.plotBtnsEnabled:
            self.enablePlotBtns(True)
        if not myBool:
            self.enablePlotBtns(False)

        # Training part...
        self.btn_addPair.setEnabled(myBool)
        self.btn_removePair.setEnabled(myBool)
        self.btn_selectFeatures.setEnabled(myBool)
        self.btn_allCombinations.setEnabled(myBool)
        for item in self.selectedFeats:
            item.setEnabled(myBool)
        self.trainingPartitions.setEnabled(myBool)
        self.fileListWidgetTrain.setEnabled(myBool)

    def getExperimentalParameters(self):
        # ----------
        # Get experimental parameters from the JSON parameters
        # ----------
        pipelineKey = self.parameterDict['pipelineType']
        newDict = settings.pipelineAcqSettings[pipelineKey].copy()
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

    def btnR2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(self.Features.Rsigned,
                       self.Features.freqs_array,
                       self.Features.electrodes_final,
                       self.Features.fres, int(self.userFmin.text()), int(self.userFmax.text()))

    def btnW2(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            plot_stats(self.Features.Wsigned,
                       self.Features.freqs_array,
                       self.Features.electrodes_final,
                       self.Features.fres, int(self.userFmin.text()), int(self.userFmax.text()))

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
                       self.electrodePsd.text(), self.Features.fres,
                       self.Features.average_baseline_cond1, self.Features.average_baseline_cond2,
                       self.Features.std_baseline_cond1, self.Features.std_baseline_cond2,
                       self.Features.electrodes_final,
                       fmin, fmax, tmin, tmax, class1, class2)

    def btnMetric(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]
            # TODO : change
            metricLabel = "Average Node Strength"
            qt_plot_metric(self.Features.power_cond1, self.Features.power_cond2,
                           self.Features.freqs_array, self.Features.electrodes_final,
                           self.electrodePsd.text(),
                           self.Features.fres, fmin, fmax, class1, class2, metricLabel)

    def btnPsd(self):
        if checkFreqsMinMax(self.userFmin.text(), self.userFmax.text(), self.samplingFreq):
            fmin = int(self.userFmin.text())
            fmax = int(self.userFmax.text())
            class1 = self.parameterDict["Class1"]
            class2 = self.parameterDict["Class2"]
            qt_plot_psd(self.Features.power_cond1, self.Features.power_cond2,
                        self.Features.freqs_array, self.Features.electrodes_final,
                        self.electrodePsd.text(),
                        self.Features.fres, fmin, fmax, class1, class2)

    def btnTopo(self):
        if self.freqTopo.text().isdigit() \
                and 0 < int(self.freqTopo.text()) < (self.samplingFreq / 2):
            print("Freq Topo: " + self.freqTopo.text())
            qt_plot_topo(self.Features.Rsigned, self.Features.electrodes_final,
                         int(self.freqTopo.text()), self.Features.fres, self.samplingFreq)
        else:
            myMsgBox("Invalid frequency for topography")

    def btnConnectSpect(self):
        qt_plot_connectSpectrum(self.Features.connect_cond1, self.Features.connect_cond2,
                                self.userChan1.text(), self.userChan2.text(), self.Features.electrodes_orig,
                                self.Features.fres, self.parameterDict["Class1"], self.parameterDict["Class2"])

    def btnConnectMatrices(self):
        if self.userFmin.text().isdigit() \
                and 0 < int(self.userFmin.text()) < (self.samplingFreq / 2) \
                and self.userFmax.text().isdigit() \
                and 0 < int(self.userFmax.text()) < (self.samplingFreq / 2):
            print("Freq connectivity matrices: " + self.userFmin.text() + " to " + self.userFmax.text())
        else:
            myMsgBox("Error in frequency used for displaying connectivity matrices...")
            return

        qt_plot_connectMatrices(self.Features.connect_cond1, self.Features.connect_cond2,
                                int(self.userFmin.text()), int(self.userFmax.text()),
                                self.Features.electrodes_orig,
                                self.parameterDict["Class1"], self.parameterDict["Class2"])

    def btnConnectome(self):
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

        qt_plot_strongestConnectome(self.Features.connect_cond1, self.Features.connect_cond2,
                                    int(self.percentStrong.text()),
                                    int(self.userFmin.text()), int(self.userFmax.text()),
                                    self.Features.electrodes_orig,
                                    self.parameterDict["Class1"], self.parameterDict["Class2"])

    def btnAddPair(self):
        self.selectedFeats.append(QLineEdit())
        self.selectedFeats[-1].setText('C4;22')
        self.qvBoxLayouts[0].addRow("Feature", self.selectedFeats[-1])

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
        if "openvibe-designer.cmd" or "openvibe-designer.exe" or "openvibe-designer.sh" in newPath:
            self.designerTextBox.setText(newPath)
            self.ovScript = newPath

        # TODO : update json file
        # ...
        return


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

def plot_stats(Rsigned, freqs_array, electrodes, fres, fmin, fmax):
    smoothing = False
    plot_Rsquare_calcul_welch(Rsigned, np.array(electrodes)[:], freqs_array, smoothing, fres, 10, fmin, fmax)
    plt.show()

def qt_plot_psd(power_cond1, power_cond2, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label):
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
                 10, fmin, fmax, fres, class1label, class2label)
        plt.show()

def qt_plot_metric(power_cond1, power_cond2, freqs_array, electrodesList, electrodeToDisp, fres, fmin, fmax, class1label, class2label, metricLabel):
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
                    10, fmin, fmax, fres, class1label, class2label, metricLabel)
        plt.show()

# Plot "Brain topography", using either Power Spectrum (in same pipeline)
# or Node Strength (or similar metric) (in Connectivity pipeline)
def qt_plot_topo(Rsigned, electrodes, frequency, fres, fs):
    topo_plot(Rsigned, round(frequency/fres), electrodes, fres, fs, 'Signed R square')
    plt.show()

# Plot "time-frequency analysis", in the POWER SPECTRUM pipeline ONLY.
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
        myMsgBox("No Electrode with this name found")
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

# Plot "connectivity spectrum" from a RAW connectivity matrix. UNUSED
def qt_plot_connectSpectrum(connect1, connect2, chan1, chan2, electrodeList, fres, class1label, class2label):
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
        plot_connect_spectrum(connect1, connect2, chan1idx, chan2idx, electrodeList, 10, fres, class1label, class2label)
        plt.show()

# Plot full RAW connectivity matrix for a given [fmin;fmax] range. UNUSED
def qt_plot_connectMatrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label):
    plot_connect_matrices(connect1, connect2, fmin, fmax, electrodeList, class1label, class2label)
    plt.show()

# Plot % of strongest nodes, from a RAW connectivity matrix, in range [fmin;fmax]. UNUSED
def qt_plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label):
    plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label)
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
