import sys
import os
import mne
import subprocess
from shutil import copyfile
import json
from threading import Thread

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QLineEdit

from PyQt5.QtGui import QFont

from modifyOpenvibeScen import *
import bcipipeline_settings as settings
from utils import *
from workspaceMgmt import *

class Dialog(QDialog):

    def __init__(self, workspace, parent=None):

        super().__init__(parent)

        # GENERAL SETTINGS (WORKSPACES, TEMPLATES...)
        self.scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.jsonfilename = "params.json"
        self.launchTrue = False

        self.workspace = workspace
        self.workspaceFolder = os.path.splitext(self.workspace)[0]
        # Create all work folders
        if not os.path.exists(self.workspaceFolder):
            myMsgBox("Specified workspace does not exist. Please use the \"Welcome\" GUI first!")
            self.reject()

        self.templateFolder = None
        self.ovScript = "C:\\openvibe-3.5.0-64bit\\bin\\openvibe-designer.exe"  # TODO : set to None in release version

        # SCENARIO PARAMETERS...
        self.parameterDict = {}
        self.parameterTextList = []  # for parsing later...

        # INTERFACE INIT...
        self.setWindowTitle('HappyFeat - Acquisition parameters GUI')
        self.dlgLayout = QVBoxLayout()

        # SPECIAL LAYOUTS...
        self.montageLayoutIdx = None
        self.customMontageLayoutIdx = None

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
        self.designerTextBox.setText(
            "C:\\openvibe-3.5.0-64bit\\bin\\openvibe-designer.exe")  # TODO set to "" in release
        self.designerTextBox.setEnabled(False)
        layout_h.addWidget(self.designerTextBox)
        layout_h.addWidget(self.btn_browseOV)
        self.vBoxLayout.addWidget(self.designerWidget)

        # Generate button
        self.btn_generateLaunch = QPushButton("Generate scenarios, launch HappyFeat")
        self.btn_generateLaunch.clicked.connect(lambda: self.generate(True))
        self.btn_generate = QPushButton("Generate scenarios, let me handle things!")
        self.btn_generate.clicked.connect(lambda: self.generate(False))

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addWidget(self.scenarioComboBox)
        self.dlgLayout.addLayout(self.vBoxLayout)
        self.dlgLayout.addWidget(self.btn_generateLaunch)
        self.dlgLayout.addWidget(self.btn_generate)

        # display layout
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
            if mtg == "standard_1020":  # default
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
        else:
            self.ovScript = None

        return

    def browseForMontage(self):
        directory = os.getcwd()
        self.customMontagePath, dummy = QFileDialog.getOpenFileName(self, "Open electrode names file", str(directory))
        # TODO : add a check on the content of the file...
        if ".txt" in self.customMontagePath:
            self.customMontageTxtBox.setText(self.customMontagePath)
        else:
            myMsgBox("Please enter a valid path for the custom montage file")

        return

    def generate(self, launch):

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

        # Acquisition parameters, set in this GUI...
        self.parameterDict["AcquisitionParams"] = {}
        for i in range(len(self.paramWidgets)):
            param = self.parameterTextList[i]
            if param in self.parameterDict:
                # TODO : remove duplication... (done to make params.json and workspace file coexist)
                self.parameterDict["AcquisitionParams"][param] = self.paramWidgets[i].text()
                self.parameterDict[param] = self.paramWidgets[i].text()

        # Write default parameters for selected pipeline
        self.parameterDict["ExtractionParams"] = {}
        self.parameterDict["ExtractionParams"]["1"] = {}
        extractParamDict = settings.pipelineExtractSettings[self.parameterDict["pipelineType"]].copy()
        for idx, (key, val) in enumerate(extractParamDict.items()):
            # TODO : remove duplication... (done to make params.json and workspace file coexist)
            self.parameterDict["ExtractionParams"]["1"][key] = str(val)
            self.parameterDict[key] = str(val)

        self.parameterDict["currentExtractId"] = "1"
        print(self.parameterDict)

        # WRITE JSON PARAMETERS FILE
        jsonfullpath = os.path.join(os.getcwd(), self.workspaceFolder, self.jsonfilename)
        with open(jsonfullpath, "w") as outfile:
            json.dump(self.parameterDict, outfile, indent=4)

        # WRITE WORKSPACE FILE
        if not self.workspace:
            # TODO !! manage error
            myMsgBox("Missing workspace file!!")
        else:
            setKeyValue(self.workspace, "ovDesignerPath", self.parameterDict["ovDesignerPath"])
            setKeyValue(self.workspace, "pipelineType", self.parameterDict["pipelineType"])
            setKeyValue(self.workspace, "sensorMontage", self.parameterDict["sensorMontage"])
            setKeyValue(self.workspace, "customMontagePath", self.parameterDict["customMontagePath"])
            setKeyValue(self.workspace, "AcquisitionParams", self.parameterDict["AcquisitionParams"])
            setKeyValue(self.workspace, "ExtractionParams", self.parameterDict["ExtractionParams"])
            setKeyValue(self.workspace, "currentExtractId", self.parameterDict["currentExtractId"])
            setKeyValue(self.workspace, "ExtractedSignalFiles", {"1": None})

        # GENERATE (list of files in settings.templateScenFilenames)
        #   SC1 (ACQ/MONITOR)
        #   SC2 (FEATURE EXT)
        #   SC2 (TRAIN)
        #   SC3 (ONLINE)
        #   SC2-SPEEDUP-FIRSTSTEP (TRAIN+, 1)
        #   SC2-SPEEDUP-FINALIZE  (TRAIN+, 2)
        for filename in settings.templateScenFilenames:
            srcFile = os.path.join(os.getcwd(), self.templateFolder, filename)
            destFile = os.path.join(os.getcwd(), self.workspaceFolder, filename)
            if os.path.exists(srcFile):
                print("---Copying file " + srcFile + " to " + destFile)
                copyfile(srcFile, destFile)
                if "xml" in destFile:
                    modifyScenarioGeneralSettings(destFile, self.parameterDict)

        # SPECIAL CASES :
        #   SC1 & SC3 : "GRAZ" BOX SETTINGS
        modifyAcqScenario(os.path.join(os.getcwd(), self.workspaceFolder, settings.templateScenFilenames[0]),
                          self.parameterDict, False)
        modifyAcqScenario(os.path.join(os.getcwd(), self.workspaceFolder, settings.templateScenFilenames[3]),
                          self.parameterDict, True)

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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Check that a workspace file has been provided
    if len(sys.argv) == 1:
        myMsgBox("NEED WORKSPACE FILE !!")
        # TODO
        sys.exit(-1)

    elif len(sys.argv) == 2:
        # Check that workspace file exists, is a json file, and contains HappyFeatVersion field...
        workspaceFile = sys.argv[1]
        workspacesFolder = "workspace"
        currScriptFolder = os.path.dirname(os.path.abspath(sys.argv[0]))
        fullWorkspacePath = os.path.join(currScriptFolder, workspacesFolder, workspaceFile)
        if not os.path.exists(fullWorkspacePath):
            myMsgBox("NEED WORKSPACE FILE !!")
            # TODO
            sys.exit(-1)
        with open(fullWorkspacePath, "r") as wp:
            workDict = json.load(wp)
            if not "HappyFeatVersion" in workDict:
                myMsgBox("INVALID WORKSPACE FILE !!")
                # TODO
                sys.exit(-1)

        dlg = Dialog(fullWorkspacePath)
        result = dlg.exec()
        # Dlg exit with error
        if not result:
            sys.exit(-1)

        # Dlg exit success
        if not dlg.getLaunch():
            # No further operation
            text = "Thanks for using the generation script!"
            myMsgBox(text)
            sys.exit(0)
        else:
            # # Launch Openvibe with acq scenario
            # acqScen = os.path.join(os.getcwd(), "generated", settings.templateScenFilenames[0])
            # command = parameterDict["ovDesignerPath"]
            # threadOV = Thread(target=launchOpenvibe, args=(command, acqScen))
            # threadOV.start()

            # Launch offline extraction interface
            threadFeat = Thread(target=featureExtractionThread, args=[fullWorkspacePath])
            threadFeat.start()

            # threadOV.join()
            threadFeat.join()

            sys.exit(0)
