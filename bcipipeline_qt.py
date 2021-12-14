import sys
import os
import pandas as pd
import time
import numpy as np

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMessageBox, QLabel, QHBoxLayout, QComboBox
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

        self.options = settings.options
        self.optionsNbParams = settings.optionsNbParams

        jsonfilename = 'C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\spectralpower-templates\\params.json'
        readJsonFile(jsonfilename)

        self.setWindowTitle('BCI Pipeline - Scenario generation')
        self.dlgLayout = QVBoxLayout()

        label = str("Welcome, BCI user! What experiment would you like to prepare?")
        self.label = QLabel(label)
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.formLayout = QFormLayout()

        self.combo = QComboBox(self)
        for i in range(len(self.options)):
            self.combo.addItem(self.options[i], i)
        self.combo.currentIndexChanged.connect(self.comboBoxChanged)
        self.formLayout.addWidget(self.combo)

        self.paramWidgets = []
        self.parameterList = []
        self.selectedScenarioName = []

        self.btn_generate = QPushButton("Generate scenarios")
        self.btn_generate.clicked.connect(lambda: self.generate())

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addLayout(self.formLayout)
        self.setLayout(self.dlgLayout)


        # display initial layout
        self.initialWindow()

    def comboBoxChanged(self, ix):
        if ix:
            # TODO : replace by "reset"
            self.combo.setEnabled(False)

            self.selectedScenarioName = self.combo.currentText()
            formLayout = QFormLayout()

            for i in range(len(settings.scenarioSettings[ix])):
                # init params...
                parameter = [settings.scenarioSettings[ix][i][0], settings.scenarioSettings[ix][i][1]]
                self.parameterList.append(parameter)
                # create widgets...
                paramWidget = QLineEdit()
                paramWidget.setText(str(settings.scenarioSettings[ix][i][1]))
                settingLabel = str(settings.scenarioSettings[ix][i][0])
                self.paramWidgets.append(paramWidget)
                formLayout.addRow(settingLabel, self.paramWidgets[i])

        self.dlgLayout.addLayout(formLayout)
        self.dlgLayout.addWidget(self.btn_generate)
        self.show()

    def initialWindow(self):
        self.show()

    def generate(self):

        #update params...
        for i in range(len(self.paramWidgets)):
            self.parameterList[i][1] = self.paramWidgets[i].text()

        #generateScenarios(self.selectedScenarioName, self.parameterList)

        text = "Thanks for using the generation script!\nYour files are in " + os.getcwd() + "/generated/"
        text += "\n\nDon't forget to double check the generated scenarios...!\nYou can now close this window."

        msg = QMessageBox()
        msg.setText(text)
        msg.exec_()
        exit(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

