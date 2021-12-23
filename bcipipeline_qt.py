import sys
import os
import pandas as pd
import time
import numpy as np
from shutil import copyfile

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

from parametersMgmt import *
from modifyOpenvibeScen import *
import bcipipeline_settings as settings

class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        # GENERATION, TEMPLATES, ETC.
        self.jsonfilename = "params.json"
        self.generatedFolder = "generated"
        self.templateFolder = None

        # SCENARIO PARAMETERS...
        self.parameterDict = {}
        self.parameterTextList = [] # for parsing later...
        self.electrodesList = ['Fp1', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6', 'T7', 'C3', 'Cz', 'C4', 'T8', 'TP9', 'CP5', 'CP1', 'CP2', 'CP6', 'TP10', 'P7', 'P3', 'Pz', 'P4', 'P8', 'PO9', 'O1', 'Oz', 'O2', 'PO10']

        # INTERFACE INIT...
        self.setWindowTitle('BCI Pipeline - Scenario generation')
        self.dlgLayout = QVBoxLayout()

        label = str("Welcome, BCI user! What experiment would you like to prepare?")
        self.label = QLabel(label)
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.formLayout = QFormLayout()

        self.selectedScenarioName = None
        self.combo = QComboBox(self)
        for idx, key in enumerate(settings.optionKeys):
            self.combo.addItem(settings.optionsComboText[key], idx)
        self.combo.currentIndexChanged.connect(self.comboBoxChanged)
        self.formLayout.addWidget(self.combo)

        self.paramWidgets = []

        # Electrodes file...
        self.electrodesFile = None
        self.btn_browse = QPushButton("Browse for electrode file...")
        self.btn_browse.clicked.connect(lambda: self.browseForElectrodeFile())
        self.electrodesFileWidget = QWidget()
        layout_h = QHBoxLayout(self.electrodesFileWidget)
        self.electrodesFileTextBox = QLineEdit()
        self.electrodesFileTextBox.setText(";".join(self.electrodesList))
        self.electrodesFileTextBox.setEnabled(True)
        layout_h.addWidget(self.electrodesFileTextBox)
        layout_h.addWidget(self.btn_browse)

        # Generate button
        self.btn_generate = QPushButton("Generate scenarios")
        self.btn_generate.clicked.connect(lambda: self.generate())

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addLayout(self.formLayout)
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
            formLayout.addRow("Electrodes List", self.electrodesFileWidget)

            self.parameterDict = {}
            self.parameterDict["pipelineType"] = pipelineKey
            # GET PARAMETER LIST FOR SELECTED BCI PIPELINE, AND DISPLAY THEM
            for param in settings.scenarioSettings[pipelineKey]:
                # init params...
                value = settings.scenarioSettings[pipelineKey][param]
                self.parameterDict[param] = value[0]
                # create widgets...
                paramWidget = QLineEdit()
                paramWidget.setText(str(value[0]))
                settingLabel = str(value[1])
                self.paramWidgets.append(paramWidget)
                self.parameterTextList.append(param)
                formLayout.addRow(settingLabel, self.paramWidgets[-1])

        self.dlgLayout.addLayout(formLayout)
        self.dlgLayout.addWidget(self.btn_generate)
        self.show()

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

    def generate(self):
        ####
        # FIRST STEP : CREATE PARAMETER DICTIONARY
        ###

        # PIPELINE DEPENDENT :
        # update params from text fields...
        overlap = None
        shift = None
        length = None
        idx = None

        for i in range(len(self.paramWidgets)):
            param = self.parameterTextList[i]
            if param in self.parameterDict:
                self.parameterDict[param] = self.paramWidgets[i].text()
            # /!\ SPECIAL CASE : Overlap becomes shift
            if param == "TimeWindowLength":
                length = self.parameterDict[param]
            elif param == "TimeWindowShift":
                overlap = self.parameterDict[param]
                idx = i

        # /!\ SPECIAL CASE : Overlap becomes shift
        shift = float(length) - float(overlap)
        print("!! REPLACING overlap " + overlap + " BY shift " + str(shift))
        self.parameterDict["TimeWindowShift"] = str(shift)

        # ALL PIPELINES : Electrode list...
        electrodes = None
        if self.electrodesFileTextBox.text() == "":
            msg = QMessageBox()
            msg.setText("Please enter a valid file containing electrode names")
            msg.exec_()
            return
        else:
            electrodes = self.electrodesFileTextBox.text()

        self.parameterDict["ChannelNames"] = electrodes
        print(self.parameterDict)

        # WRITE JSON PARAMETERS FILE
        jsonfullpath = os.path.join(os.getcwd(), self.generatedFolder, self.jsonfilename)
        with open(jsonfullpath, "w") as outfile:
            json.dump(self.parameterDict, outfile, indent = 4)

        # GENERATE (list of files in settings.templateScenFilenames)
        #   SC1 (ACQ/MONITOR)
        #   SC2 (FEATURE EXT)
        #   SC2 (TRAIN)
        #   SC3 (ONLINE)
        for filename in settings.templateScenFilenames:
            srcFile = os.path.join(os.getcwd(), self.templateFolder, filename)
            destFile = os.path.join(os.getcwd(), self.generatedFolder, filename)
            print("---Copying file " + srcFile + " to " + destFile)
            copyfile(srcFile, destFile)
            modifyScenarioGeneralSettings(destFile, self.parameterDict)

        # SPECIAL CASES :
        #   SC1 & SC3 : "GRAZ" BOX SETTINGS
        modifyAcqScenario(os.path.join(os.getcwd(), self.generatedFolder, settings.templateScenFilenames[0]),
                          self.parameterDict)
        modifyAcqScenario(os.path.join(os.getcwd(), self.generatedFolder, settings.templateScenFilenames[3]),
                          self.parameterDict)

        text = "Thanks for using the generation script!\nYour files are in " + os.getcwd() + "/generated/"
        text += "\n\n(Don't forget to double check the generated scenarios...!)\nYou can now close this window."

        msg = QMessageBox()
        msg.setText(text)
        msg.exec_()
        exit(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

