import sys
import os
import mne
import subprocess
from multiprocessing import Process
from shutil import copyfile
import json
from threading import Thread
import pandas as pd
from importlib import resources

from PySide2 import QtCore
from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtWidgets import QFormLayout
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QComboBox
from PySide2.QtWidgets import QFileDialog
from PySide2.QtWidgets import QMessageBox
from PySide2.QtWidgets import QDialog
from PySide2.QtWidgets import QPushButton
from PySide2.QtWidgets import QLineEdit

from PySide2.QtGui import QFont

from happyfeat.lib.modifyOpenvibeScen import *
import happyfeat.lib.bcipipeline_settings as settings
from happyfeat.lib.utils import *
import happyfeat.lib.workspaceMgmt as workspaceMgmt

import happyfeat.featureExtractionInterface as featExtractApp

class Dialog(QDialog):

    def __init__(self, workspace, parent=None):

        super().__init__(parent)

        # GENERAL SETTINGS (WORKSPACES, TEMPLATES...)
        self.launchTrue = False
        self.ovScript = None    # to be r/w in config.json
        self.customMontagePath = None
        self.templateFolder = None
        self.workspace = workspace  # fullpath of the .hfw file
        self.workspaceFolder = os.path.splitext(self.workspace)[0]  # only the folder (still fullpath)
        if not os.path.exists(self.workspace) or not os.path.exists(self.workspaceFolder):
            myMsgBox("Specified workspace does not exist. Please use the \"Welcome\" GUI first!")
            self.reject()

        # Get user's config
        self.userConfig = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        if not os.path.exists(self.userConfig):
            myMsgBox("General config file config.json not found! Please use happyfeat_welcome.py script.")
            self.reject()
        with open(self.userConfig, "r+") as userCfg:
            currentCfg = json.load(userCfg)
            if "lastWorkspacePath" in currentCfg:
                self.workspacesFolder = currentCfg["lastWorkspacePath"]
            if "ovScript" in currentCfg:
                self.ovScript = currentCfg["ovScript"]

        # SCENARIO PARAMETERS...
        self.parameterDict = {}
        self.parameterTextList = []  # for parsing later...

        # INTERFACE INIT...
        self.setWindowTitle('HappyFeat - Acquisition parameters GUI')
        self.dlgLayout = QVBoxLayout()

        # SPECIAL LAYOUTS...
        self.montageLayoutIdx = None
        self.customMontageLayoutIdx = None

        # Start listing the widgets, we'll add them to the layout at the end
        label = str("=== Protocol Selection ===")
        self.label = QLabel(label)
        self.label.setFont(QFont("system-ui", 12))
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.scenarioComboBox = QComboBox(self)
        for idx, key in enumerate(settings.optionKeys):
            self.scenarioComboBox.addItem(settings.optionsComboText[key], idx)
        # self.scenarioComboBox.currentIndexChanged.connect(self.scenarioComboBoxChanged)

        # COLUMN OF PARAMETERS
        self.vBoxLayout = QVBoxLayout()
        self.vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

        # ACQ PARAMETERS
        self.paramWidgets = []
        self.initAcqParams()

        # OpenViBE designer executable...
        labelOv = QLabel()
        labelOvtxt = str("OpenViBE designer script (openvibe-designer.cmd or .exe or .sh)")
        labelOvtxt = str(labelOvtxt + "\n(in your OpenViBE installation folder)")
        labelOv.setText(labelOvtxt)
        labelOv.setAlignment(QtCore.Qt.AlignCenter)
        self.vBoxLayout.addWidget(labelOv)

        self.btn_browseOV = QPushButton("Browse...")
        self.btn_browseOV.clicked.connect(lambda: self.browseForDesigner())
        self.designerWidget = QWidget()
        layout_h = QHBoxLayout(self.designerWidget)
        self.designerTextBox = QLineEdit()
        self.designerTextBox.setText(self.ovScript)
        self.designerTextBox.setEnabled(False)
        layout_h.addWidget(self.designerTextBox)
        layout_h.addWidget(self.btn_browseOV)
        self.vBoxLayout.addWidget(self.designerWidget)

        # Generate button
        self.btn_generateLaunch = QPushButton("Generate scenarios, launch HappyFeat")
        self.btn_generateLaunch.clicked.connect(lambda: self.generate(True))
        # self.btn_generate = QPushButton("Generate scenarios, let me handle things!")
        # self.btn_generate.clicked.connect(lambda: self.generate(False))

        # Add all widgets to the general layout...
        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addWidget(self.scenarioComboBox)
        self.dlgLayout.addLayout(self.vBoxLayout)
        self.dlgLayout.addWidget(self.btn_generateLaunch)
        # self.dlgLayout.addWidget(self.btn_generate)

        # Display layout
        self.setLayout(self.dlgLayout)
        self.show()

    def initAcqParams(self):

        # PARAMETERS
        labelText = [None, None]
        label = [None, None]
        labelText[0] = str("=== ")
        labelText[0] = str(labelText[0] + "Acquisition and Stimulation")
        labelText[0] = str(labelText[0] + " ===")
        label[0] = QLabel(labelText[0])
        label[0].setAlignment(QtCore.Qt.AlignCenter)
        label[0].setFont(QFont("system-ui", 12))
        self.vBoxLayout.addWidget(label[0])

        # PARAMETER ALWAYS PRESENT : ELECTRODES MONTAGE
        # Drop-down menu with montages available in MNE
        # + Custom option (will open a file selection in the future... TODO)
        self.layoutMontages = QVBoxLayout()
        self.layoutMontageSelectionH = QHBoxLayout()
        self.layoutMontageV1 = QVBoxLayout()
        self.layoutMontageV2 = QVBoxLayout()
        labelMontage = QLabel()
        labelMontage.setText("Channel Montage")
        self.layoutMontageV1.addWidget(labelMontage)
        self.layoutMontageV1.setAlignment(QtCore.Qt.AlignTop)
        self.montageComboBox = QComboBox(self)
        montageIdx = 0
        self.montageComboBox.addItem("Custom... (select file)")
        for idx, mtg in enumerate(mne.channels.get_builtin_montages()):
            self.montageComboBox.addItem(mtg)
            if mtg == "biosemi64":  # default
                montageIdx = idx + 1

        self.montageComboBox.setCurrentIndex(montageIdx)
        self.montageComboBox.currentIndexChanged.connect(self.montageComboBoxChanged)
        self.layoutMontageV2.addWidget(self.montageComboBox)
        self.layoutMontageSelectionH.addLayout(self.layoutMontageV1)
        self.layoutMontageSelectionH.addLayout(self.layoutMontageV2)
        self.layoutMontages.addLayout(self.layoutMontageSelectionH)

        self.vBoxLayout.addLayout(self.layoutMontages)

        # OTHER PARAMETERS

        formLayout = None
        formLayout = QFormLayout()

        # GET PARAMETER LIST FOR SELECTED BCI PIPELINE, AND DISPLAY THEM
        for idx, param in enumerate(settings.pipelineAcqSettings):
            # init params...
            value = settings.pipelineAcqSettings[param]
            self.parameterDict[param] = value
            # create widgets...
            paramWidget = QLineEdit()
            paramWidget.setText(str(value))
            settingLabel = settings.paramIdText[param]
            self.paramWidgets.append(paramWidget)
            self.parameterTextList.append(param)
            formLayout.addRow(settingLabel, self.paramWidgets[-1])

        self.vBoxLayout.addLayout(formLayout)

        return

    def montageComboBoxChanged(self, ix):
        if ix == 0:  # Custom
            # open new layout to let user choose montage file
            self.btn_browseMontage = QPushButton("Browse...")
            self.btn_browseMontage.clicked.connect(lambda: self.browseForMontage())
            self.customMontageWidget = QWidget()
            layout_h = QHBoxLayout(self.customMontageWidget)
            self.customMontageTxtBox = QLineEdit()
            self.customMontageTxtBox.setText("")
            self.customMontageTxtBox.setEnabled(False)
            layout_h.addWidget(self.customMontageTxtBox)
            layout_h.addWidget(self.btn_browseMontage)
            self.layoutMontageV2.addWidget(self.customMontageWidget)

        else:
            # if "custom" layout had been opened before, remove it.
            if self.layoutMontageV2.count() > 1:
                self.btn_browseMontage.setParent(None)
                self.customMontageWidget.setParent(None)
                self.customMontageTxtBox.setParent(None)
                self.layoutMontageV2.removeItem(self.layoutMontageV2.itemAt(1))

        return

    def browseForDesigner(self):
        directory = os.getcwd()
        self.ovScript, dummy = QFileDialog.getOpenFileName(self, "OpenViBE designer script", str(directory))
        if "openvibe-designer.cmd" or "openvibe-designer.exe" or "openvibe-designer.sh" in self.ovScript:
            self.designerTextBox.setText(self.ovScript)
            workspaceMgmt.setKeyValue(self.userConfig, "ovScript", self.ovScript)
        else:
            self.ovScript = None

        return

    def browseForMontage(self):
        directory = os.getcwd()
        self.customMontagePath, dummy = QFileDialog.getOpenFileName(self, "Open electrode names file", str(directory))
        if self.checkCustomMontage():
            self.customMontageTxtBox.setText(self.customMontagePath)

        return

    def checkCustomMontage(self):
        invalid = False
        column_names = ['name', 'x', 'y', 'z']
        csv = pd.read_csv(self.customMontagePath)
        if len(csv.columns) != len(column_names):
            myMsgBox("Invalid channel locations file. Please refer to the documentation.")
            return False
        if not all(csv.columns[x] == column_names[x] for x in range(len(column_names))):
            myMsgBox("Invalid channel locations file. Please refer to the documentation.")
            return False

        return True

    def generate(self, launch):

        if self.ovScript == "" or not self.ovScript:
            myMsgBox("Please enter a correct path for the OpenViBE designer")
            return

        ix = self.scenarioComboBox.currentIndex()
        if ix == 0:
            myMsgBox("Please select a protocol...")
            return

        pipelineKey = settings.optionKeys[ix]

        self.templateFolder = settings.optionsTemplatesDir[pipelineKey]
        print(str("TEMPLATE FOLDER : " + self.templateFolder))

        self.parameterDict["pipelineType"] = pipelineKey

        ####
        # FIRST STEP : CREATE PARAMETER DICTIONARY
        ###

        # OpenViBE Path...
        if self.ovScript is None:
            myMsgBox("Please enter a valid path for the openViBE designer script")
            return

        if self.montageComboBox.currentIndex() == 0:  # custom
            if self.customMontagePath is None:
                myMsgBox("Please provide a valid file for the custom montage")
                return

        # Montage : default values...
        self.parameterDict["sensorMontage"] = self.montageComboBox.currentText()
        self.parameterDict["customMontagePath"] = ''
        if self.montageComboBox.currentIndex() == 0:
            self.parameterDict["sensorMontage"] = "custom"
            self.parameterDict["customMontagePath"] = self.customMontagePath

        # self.parameterDict["ChannelNames"] = electrodes
        self.parameterDict["ovDesignerPath"] = self.ovScript

        self.parameterDict["Sessions"] = {}

        # Acquisition parameters, set in this GUI...
        self.parameterDict["AcquisitionParams"] = {}
        for i in range(len(self.paramWidgets)):
            param = self.parameterTextList[i]
            if param in self.parameterDict:
                # TODO : remove duplication... (done to make params.json and workspace file coexist)
                self.parameterDict["AcquisitionParams"][param] = self.paramWidgets[i].text()
                self.parameterDict[param] = self.paramWidgets[i].text()

        # Write default parameters for selected pipeline
        extractParamDict = settings.pipelineExtractSettings[self.parameterDict["pipelineType"]].copy()

        self.parameterDict["currentSessionId"] = "1"
        print(self.parameterDict)

        # WRITE WORKSPACE FILE
        if not self.workspace:
            # TODO !! manage error
            myMsgBox("Missing workspace file!!")
        else:
            workspaceMgmt.setKeyValue(self.workspace, "ovDesignerPath", self.parameterDict["ovDesignerPath"])
            workspaceMgmt.setKeyValue(self.workspace, "pipelineType", self.parameterDict["pipelineType"])
            workspaceMgmt.setKeyValue(self.workspace, "sensorMontage", self.parameterDict["sensorMontage"])
            workspaceMgmt.setKeyValue(self.workspace, "customMontagePath", self.parameterDict["customMontagePath"])
            workspaceMgmt.setKeyValue(self.workspace, "AcquisitionParams", self.parameterDict["AcquisitionParams"])
            workspaceMgmt.setKeyValue(self.workspace, "currentSessionId", self.parameterDict["currentSessionId"])
            workspaceMgmt.newSession(self.workspace, self.parameterDict, "1", extractParamDict)

        # GENERATE (list of files in settings.templateScenFilenames)
        #   SC1 (ACQ/MONITOR)
        #   SC2 (FEATURE EXT)
        #   SC2 (TRAIN)
        #   SC3 (ONLINE)
        #   SC2-SPEEDUP-FIRSTSTEP (TRAIN+, 1)
        #   SC2-SPEEDUP-FINALIZE  (TRAIN+, 2)
        for filename in settings.templateScenFilenames:
            with resources.path(str(__name__.split('.')[0] + '.' + self.templateFolder), filename) as srcFile:
                destFile = os.path.join(self.workspaceFolder, filename)
                if os.path.exists(srcFile):
                    print("---Copying file " + str(srcFile) + " to " + str(destFile))
                    copyfile(srcFile, destFile)
                    if "xml" in destFile:
                        modifyScenarioGeneralSettings(destFile, self.parameterDict)

        # SPECIAL CASES :
        #   SC1 & SC3 : "GRAZ" BOX SETTINGS
        modifyAcqScenario(os.path.join(self.workspaceFolder,
                                       settings.templateScenFilenames[0]), self.parameterDict, False)
        modifyAcqScenario(os.path.join(self.workspaceFolder,
                                       settings.templateScenFilenames[3]), self.parameterDict, True)

        if launch:
            self.launchTrue = True

        # Exit with success
        self.accept()

    def closeEvent(self, event):
        self.reject()

    def getLaunch(self):
        return self.launchTrue

    def setWorkspace(self, workspace):
        self.workspace = workspace
        return

def featureExtractionThread(workspace):
    p = subprocess.Popen(["python", "2-featureExtractionInterface.py", fullWorkspacePath],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        output = p.stdout.readline()
        if p.poll() is not None:
            break
        if output:
            print(str(output))
            if "Process finished with exit code" in str(output):
                break
    return

def launchOpenvibe(command, acqScen):
    p = subprocess.Popen([command, "--open", acqScen],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        output = p.stdout.readline()
        if p.poll() is not None:
            break
        if output:
            print(str(output))
            if "Application terminated" in str(output):
                break
    return


def launch(folder, fullWorkspacePath):
    app = QApplication(sys.argv)

    # Check that workspace file exists, is a json file, and contains HappyFeatVersion field...
    if not os.path.exists(fullWorkspacePath):
        myMsgBox("NEED FULL WORKSPACE FILE !!")
        # TODO
        return -1
    with open(fullWorkspacePath, "r") as wp:
        workDict = json.load(wp)
        if not "HappyFeatVersion" in workDict:
            myMsgBox("INVALID WORKSPACE FILE !!")
            # TODO
            return -1

    dlg = Dialog(fullWorkspacePath)
    result = dlg.exec()
    # Dlg exit with error
    if not result:
        return -1

    # Dlg exit success
    if not dlg.getLaunch():
        # No further operation
        text = "Thanks for using the generation script!"
        myMsgBox(text)
        return 0
    else:
        # # Launch Openvibe with acq scenario
        # acqScen = os.path.join(os.getcwd(), "generated", settings.templateScenFilenames[0])
        # command = parameterDict["ovDesignerPath"]
        # threadOV = Thread(target=launchOpenvibe, args=(command, acqScen))
        # threadOV.start()

        # Launch offline extraction interface
        p = Process(target=featExtractApp.launch, args=(folder, fullWorkspacePath))
        p.start()
        p.join()

    return app.exec_()


if __name__ == '__main__':
    retVal = -1
    # Check that a workspace file has been provided
    if len(sys.argv) == 1:
        myMsgBox("NEED WORKSPACE FILE !!")
        # TODO
        sys.exit(-1)

    elif len(sys.argv) == 2:
        folder = os.path.dirname(os.path.abspath(sys.argv[0]))
        retVal = launch(folder, sys.argv[1])

    sys.exit(retVal)
