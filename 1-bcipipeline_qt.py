import sys
import os
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

class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        # GENERATION, TEMPLATES, ETC.
        self.jsonfilename = "params.json"
        self.generatedFolder = "generated"
        self.templateFolder = None
        # self.ovScript = "C:\\openvibeDevelop_update\\dist\\x64\\Release\\openvibe-designer.cmd"  # TODO : set to None in release version
        self.ovScript = "C:\\openvibe-3.5.0-64bit\\bin\\openvibe-designer.exe"  # TODO : set to None in release version

        # SCENARIO PARAMETERS...
        self.parameterDict = {}
        self.parameterTextList = []  # for parsing later...
        # self.electrodesList = ['Fp1', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6', 'T7', 'C3', 'Cz', 'C4', 'T8', 'TP9', 'CP5', 'CP1', 'CP2', 'CP6', 'TP10', 'P7', 'P3', 'Pz', 'P4', 'P8', 'PO9', 'O1', 'Oz', 'O2', 'PO10']

        # INTERFACE INIT...
        #self.setWindowTitle('goodViBEs - an easy openViBE-based GUI')
        self.setWindowTitle('Pipeline Generation GUI')
        self.dlgLayout = QVBoxLayout()

        label = str("=== Protocol Selection ===")
        self.label = QLabel(label)
        self.label.setFont(QFont("system-ui", 12))
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.selectedScenarioName = None
        self.combo = QComboBox(self)
        for idx, key in enumerate(settings.optionKeys):
            self.combo.addItem(settings.optionsComboText[key], idx)
        self.combo.currentIndexChanged.connect(self.comboBoxChanged)

        self.paramWidgets = []

        # Electrodes file...
        self.electrodesFile = None
        # self.btn_browse = QPushButton("Browse for electrode file...")
        # self.btn_browse.clicked.connect(lambda: self.browseForElectrodeFile())
        # self.electrodesFileWidget = QWidget()
        # layout_h = QHBoxLayout(self.electrodesFileWidget)
        # self.electrodesFileTextBox = QLineEdit()
        # self.electrodesFileTextBox.setText(";".join(self.electrodesList))
        # self.electrodesFileTextBox.setEnabled(True)
        # layout_h.addWidget(self.electrodesFileTextBox)
        # layout_h.addWidget(self.btn_browse)

        # Generate button
        self.btn_generateLaunch = QPushButton("Generate scenarios, launch HappyFeat")
        self.btn_generateLaunch.clicked.connect(lambda: self.generate(True))
        self.btn_generate = QPushButton("Generate scenarios, let me handle things!")
        self.btn_generate.clicked.connect(lambda: self.generate(False))

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addWidget(self.combo)
        # self.dlgLayout.addLayout(self.formLayout)
        self.setLayout(self.dlgLayout)

        # display initial layout
        self.initialWindow()

    def comboBoxChanged(self, ix):
        if ix:
            pipelineKey = settings.optionKeys[ix]

            # TODO : replace by "reset" later on ?
            self.combo.setEnabled(False)

            self.templateFolder = settings.optionsTemplatesDir[pipelineKey]
            print(str("TEMPLATE FOLDER : " + self.templateFolder))

            self.selectedScenarioName = self.combo.currentText()
            formLayout = QFormLayout()

            # PARAMETER ALWAYS PRESENT : LIST OF CHANNELS
            # formLayout.addRow("Electrodes List", self.electrodesFileWidget)
            # self.dlgLayout.addLayout(formLayout)

            # COLUMN OF PARAMETERS
            vBoxLayout = QVBoxLayout()

            self.parameterDict = {}

            labelText = [None, None]
            label = [None, None]
            labelText[0] = str("=== ")
            labelText[0] = str(labelText[0] + "Acquisition and Stimulation")
            labelText[0] = str(labelText[0] + " ===")
            label[0] = QLabel(labelText[0])
            label[0].setAlignment(QtCore.Qt.AlignCenter)
            label[0].setFont(QFont("system-ui", 12))
            vBoxLayout.addWidget(label[0])

            formLayout = None
            formLayout = QFormLayout()

            self.parameterDict["pipelineType"] = pipelineKey

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

            vBoxLayout.addLayout(formLayout)
            vBoxLayout.setAlignment(QtCore.Qt.AlignTop)

            # OpenViBE designer file...
            labelOv = QLabel()
            labelOvtxt = str("OpenViBE designer script (openvibe-designer.cmd or .exe or .sh)")
            labelOvtxt = str(labelOvtxt + "\n(in your OpenViBE installation folder)")
            labelOv.setText(labelOvtxt)
            labelOv.setAlignment(QtCore.Qt.AlignCenter)
            vBoxLayout.addWidget(labelOv)

            self.btn_browseOV = QPushButton("Browse...")
            self.btn_browseOV.clicked.connect(lambda: self.browseForDesigner())
            self.designerWidget = QWidget()
            layout_h = QHBoxLayout(self.designerWidget)
            self.designerTextBox = QLineEdit()
            self.designerTextBox.setText("C:\\openvibe-3.5.0-64bit\\bin\\openvibe-designer.exe")  # TODO set to "" in release
            self.designerTextBox.setEnabled(False)
            layout_h.addWidget(self.designerTextBox)
            layout_h.addWidget(self.btn_browseOV)
            vBoxLayout.addWidget(self.designerWidget)

            self.dlgLayout.addLayout(vBoxLayout)
            self.dlgLayout.addWidget(self.btn_generateLaunch)
            self.dlgLayout.addWidget(self.btn_generate)
            self.show()

    def browseForDesigner(self):
        directory = os.getcwd()
        self.ovScript, dummy = QFileDialog.getOpenFileName(self, "OpenViBE designer script", str(directory))
        if "openvibe-designer.cmd" or "openvibe-designer.exe" or "openvibe-designer.sh" in self.ovScript:
            self.designerTextBox.setText(self.ovScript)
        else:
            self.ovScript = None

        return

    def browseForElectrodeFile(self):
        directory = os.getcwd()
        self.electrodesFile, dummy = QFileDialog.getOpenFileName(self, "Open electrode names file", str(directory))
        if self.electrodesFile:
            electrodes = []
            with open(self.electrodesFile) as f:
                lines = f.readlines()
                for elec in lines:
                    electrodes.append(elec.rstrip("\n"))
            self.electrodesFileTextBox.setText(";".join(electrodes))

    def initialWindow(self):
        self.show()

    def generate(self, launch):
        ####
        # FIRST STEP : CREATE PARAMETER DICTIONARY
        ###

        # OpenViBE Path...
        if self.ovScript is None:
            myMsgBox("Please enter a valid path for the openViBE designer script")
            return

        # self.parameterDict["ChannelNames"] = electrodes
        self.parameterDict["ovDesignerPath"] = self.ovScript

        # Acquisition parameters, set in this GUI...
        for i in range(len(self.paramWidgets)):
            param = self.parameterTextList[i]
            if param in self.parameterDict:
                self.parameterDict[param] = self.paramWidgets[i].text()

        # Write default parameters for selected pipeline
        extractParamDict = settings.pipelineExtractSettings[self.parameterDict["pipelineType"]].copy()
        for idx, (key, val) in enumerate(extractParamDict.items()):
            self.parameterDict[key] = str(val)

        print(self.parameterDict)

        # WRITE JSON PARAMETERS FILE
        jsonfullpath = os.path.join(os.getcwd(), self.generatedFolder, self.jsonfilename)
        with open(jsonfullpath, "w") as outfile:
            json.dump(self.parameterDict, outfile, indent=4)

        # GENERATE (list of files in settings.templateScenFilenames)
        #   SC1 (ACQ/MONITOR)
        #   SC2 (FEATURE EXT)
        #   SC2 (TRAIN)
        #   SC3 (ONLINE)
        #   SC2-SPEEDUP-FIRSTSTEP (TRAIN+, 1)
        #   SC2-SPEEDUP-FINALIZE  (TRAIN+, 2)
        for filename in settings.templateScenFilenames:
            srcFile = os.path.join(os.getcwd(), self.templateFolder, filename)
            destFile = os.path.join(os.getcwd(), self.generatedFolder, filename)
            if os.path.exists(srcFile):
                print("---Copying file " + srcFile + " to " + destFile)
                copyfile(srcFile, destFile)
                if "xml" in destFile:
                    modifyScenarioGeneralSettings(destFile, self.parameterDict)

        # SPECIAL CASES :
        #   SC1 & SC3 : "GRAZ" BOX SETTINGS
        modifyAcqScenario(os.path.join(os.getcwd(), self.generatedFolder, settings.templateScenFilenames[0]),
                          self.parameterDict, False)
        modifyAcqScenario(os.path.join(os.getcwd(), self.generatedFolder, settings.templateScenFilenames[3]),
                          self.parameterDict, True)

        if launch:
            self.accept()
        else:
            text = "Thanks for using the generation script!\nYour scenarios are in \n\t" + os.getcwd() + "\\generated\\"
            text += "\n\nYou can also run the Analysis/Training app:\n\t" + os.getcwd() + "2-featureExtractionInterface.py"
            myMsgBox(text)
            self.reject()

    def closeEvent(self, event):
        self.reject()

def myMsgBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.exec_()
    return

def featureExtractionThread():
    p = subprocess.Popen(["python", "2-featureExtractionInterface.py"],
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
    dlg = Dialog()
    result = dlg.exec()
    if not result:
        sys.exit(-1)

    # Get current script path, and openvibe Designer from params.json
    scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
    print(scriptPath)
    jsonfullpath = os.path.join(scriptPath, "generated", "params.json")
    with open(jsonfullpath) as jsonfile:
        parameterDict = json.load(jsonfile)

    # Launch Openvibe with acq scenario
    acqScen = os.path.join(os.getcwd(), "generated", settings.templateScenFilenames[0])
    command = parameterDict["ovDesignerPath"]
    threadOV = Thread(target=launchOpenvibe, args=(command, acqScen))
    threadOV.start()

    # Launch offline extraction interface
    threadFeat = Thread(target=featureExtractionThread)
    threadFeat.start()

    threadOV.join()
    threadFeat.join()

    sys.exit()
