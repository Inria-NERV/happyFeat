import sys
import os
import pandas as pd
import time
import numpy as np

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox, QLabel, QHBoxLayout, QComboBox, QFileDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QVBoxLayout

from parametersMgmt import *
from modifyOpenvibeScen import *
from generateOpenVibeScenario import *
import bcipipeline_settings as settings

class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        # GENERATION, TEMPLATES, ETC.
        self.jsonfilename = "params.json"
        self.generatedFolder = "generated"
        self.templateFolder = None

        # SCENARIO PARAMETERS...
        self.options = settings.options
        self.optionsNbParams = settings.optionsNbParams
        self.parameterList = []
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
        for i in range(len(self.options)):
            self.combo.addItem(self.options[i], i)
        self.combo.currentIndexChanged.connect(self.comboBoxChanged)
        self.formLayout.addWidget(self.combo)

        self.paramWidgets = []

        # Electrodes file...
        self.electrodesFile = None
        self.btn_browse = QPushButton("Browse")
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
            # TODO : replace by "reset" later on ?
            self.combo.setEnabled(False)

            self.templateFolder = settings.optionsTemplatesDir[ix]
            print(str("TEMPLATE FOLDER : " + self.templateFolder))

            self.selectedScenarioName = self.combo.currentText()
            formLayout = QFormLayout()

            # PARAMETER ALWAYS PRESENT : LIST OF CHANNELS
            formLayout.addRow("Electrode names file", self.electrodesFileWidget)

            # GET PARAMETER LIST FOR SELECTED BCI PIPELINE, AND DISPLAY THEM
            for i in range(len(settings.scenarioSettings[ix])):
                # init params...
                parameter = [settings.scenarioSettings[ix][i][0], settings.scenarioSettings[ix][i][1]]
                self.parameterList.append(parameter)
                # create widgets...
                paramWidget = QLineEdit()
                paramWidget.setText(str(settings.scenarioSettings[ix][i][1]))
                settingLabel = str(settings.scenarioSettings[ix][i][2])
                self.paramWidgets.append(paramWidget)
                formLayout.addRow(settingLabel, self.paramWidgets[i])

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
        # PIPELINE DEPENDENT : update params from text fields...
        for i in range(len(self.paramWidgets)):
            self.parameterList[i][1] = self.paramWidgets[i].text()

        # ALL PIPELINES : Electrode list...
        electrodes = None
        if self.electrodesFileTextBox.text() == "":
            msg = QMessageBox()
            msg.setText("Please enter a valid file containing electrode names")
            msg.exec_()
            return
        else:
            electrodes = self.electrodesFileTextBox.text()

        self.parameterList.append(["ChannelNames", electrodes])
        print(self.parameterList)

        # WRITE JSON PARAMETERS FILE
        # TODO !
        jsonfullpath = os.path.join(os.getcwd(), self.templateFolder, self.jsonfilename)
        readJsonFile(jsonfullpath)

        # GENERATE SC1 (ACQ/MONITOR) + SC2 (FEATURE EXT) + SC2 (TRAIN) + SC3 (ONLINE)
        # generateScenarios(self.selectedScenarioName, self.parameterList)
        for filename in settings.templateScenFilenames:
            srcFile = os.path.join(os.getcwd(), self.templateFolder, filename)
            destFile = os.path.join(os.getcwd(), self.generatedFolder, filename)
            print("Copying file " + srcFile + " to " + destFile)
            # ...

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

