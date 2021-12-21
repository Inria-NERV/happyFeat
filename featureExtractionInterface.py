import sys
import os
import pandas as pd
import time
import numpy as np
import matplotlib.pyplot as plt

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication,QMessageBox,QLabel,QHBoxLayout
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QVBoxLayout

from Visualization_Data import *
from featureExtractUtils import *
from parametersMgmt import *
from modifyOpenvibeScen import *


class Features:
    Rsigned = []
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

        jsonfilename = 'C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\spectralpower-templates\\params.json'
        readJsonFile(jsonfilename)

        self.setWindowTitle('Feature Extraction')
        self.dlgLayout = QVBoxLayout()

        # FEATURE VISUALIZATION PART
        self.label = QLabel('----- VISUALIZE FEATURES -----')
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        self.formLayout = QFormLayout()

        # Param 1 : Path 1
        self.path1 = QLineEdit()
        self.path1.setText(
            'C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\spectralpower-templates\\spectrumAmplitude-Left.csv')
        self.formLayout.addRow('Path:', self.path1)
        # Param 2 : Path 2
        self.path2 = QLineEdit()
        self.path2.setText(
            'C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\spectralpower-templates\\spectrumAmplitude-Right.csv')
        self.formLayout.addRow('Name File', self.path2)

        # Param 3 : Electrode to use for PSD display
        self.userFmax = QLineEdit()
        self.userFmax.setText('40')
        self.formLayout.addRow('fMax (for PSD and r2map)', self.userFmax)

        # Param 3 : Electrode to use for PSD display
        self.electrodePsd = QLineEdit()
        self.electrodePsd.setText('FC1')
        self.formLayout.addRow('Electrode to use for PSD', self.electrodePsd)
        # Param 4 : Frequency to use for Topography
        self.freqTopo = QLineEdit()
        self.freqTopo.setText('15')
        self.formLayout.addRow('Frequency to use for Topography (Hz)', self.freqTopo)

        self.btn_load_files = QPushButton("Load spectrum files")
        self.btn_r2map = QPushButton("Plot R2Map")
        self.btn_timefreq = QPushButton("Plot Time/Freq Analysis")
        self.btn_psd = QPushButton("Plot PSD for Spec. Freq.")
        self.btn_topo = QPushButton("Plot Topography for Spec. Freq.")
        self.btn_psd_r2 = QPushButton("Plot R2 and PSD")

        # FEATURE SELECTION PART
        self.label2 = QLabel('----- SELECT FEATURES FOR TRAINING -----')
        self.label2.setAlignment(QtCore.Qt.AlignCenter)
        textFeatureSelect = "Enter pair : ELECTRODE;FREQUENCY (separated with \";\")"
        textFeatureSelect = str(textFeatureSelect + "\n(Use \":\" for frequency range)")
        textFeatureSelect = str(textFeatureSelect + "\n  Ex: FCz;14:22")
        textFeatureSelect = str(textFeatureSelect + "\n  Ex: C4;22")
        self.label3 = QLabel(textFeatureSelect)

        self.formLayoutOutput = QFormLayout()
        self.selectedFeats = []
        # Param Output 1 : First selected pair of Channels / Electrodes
        # We'll add more with a button
        self.selectedFeats.append(QLineEdit())
        self.selectedFeats[0].setText('')
        pairText = "Selected Feats Pair"
        self.formLayoutOutput.addRow(pairText, self.selectedFeats[0])

        self.btn_addPair = QPushButton("Add Feature")
        self.btn_removePair = QPushButton("Remove Last Feat")
        self.btn_selectFeatures = QPushButton("Select features & generate scenarios")

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addLayout(self.formLayout)
        self.dlgLayout.addWidget(self.btn_load_files)
        self.dlgLayout.addWidget(self.btn_r2map)
        self.dlgLayout.addWidget(self.btn_timefreq)
        self.dlgLayout.addWidget(self.btn_psd)
        self.dlgLayout.addWidget(self.btn_topo)
        self.dlgLayout.addWidget(self.btn_psd_r2)
        self.dlgLayout.addWidget(self.label2)
        self.dlgLayout.addWidget(self.label3)
        self.dlgLayout.addLayout(self.formLayoutOutput)
        self.dlgLayout.addWidget(self.btn_addPair)
        self.dlgLayout.addWidget(self.btn_removePair)
        self.dlgLayout.addWidget(self.btn_selectFeatures)

        self.setLayout(self.dlgLayout)

        # Other inits...
        self.dataNp1 = []
        self.dataNp2 = []
        self.Features = Features()
        self.PipelineParams = PipelineParams()

        # display initial layout
        self.initialWindow()

    def load_files(self, path1, path2):
        data1 = load_csv_cond(path1)
        data2 = load_csv_cond(path2)
        if data1.empty or data2.empty:
            msg = QMessageBox()
            msg.setText("Please wait while OpenViBE finishes writing CSV files.")
            msg.exec_()
        else:
            self.dataNp1 = data1.to_numpy()
            self.dataNp2 = data2.to_numpy()
            self.extract_features()
            self.plotWindow()

    def extract_features(self):
        time = self.PipelineParams.trialLengthSec
        trials = self.PipelineParams.trialNb
        nbElectrodes = len(self.PipelineParams.electrodeList)
        n_bins = self.PipelineParams.fftBins
        winLen = self.PipelineParams.burgWindowLength
        winOverlap = self.PipelineParams.burgWindowOverlap

        power_right, power_left, time_left, time_right, time_length = Extract_Data_to_compare(self.dataNp1,
                                                                                              self.dataNp2,
                                                                                              time, trials,
                                                                                              nbElectrodes,
                                                                                              n_bins,
                                                                                              winLen, winOverlap)

        # Statistical Analysis
        electrodes_orig = channel_generator(nbElectrodes, 'TP9', 'TP10')
        freqs_left = np.arange(0, n_bins)
        Rsigned = Compute_Rsquare_Map_Welch(power_right[:, :, :(n_bins-1)], power_left[:, :, :(n_bins-1)])
        # Rsigned = Compute_Rsquare_Map_Welch(power_right[:, :, :(fs/2)], power_left[:, :, :(fs/2)])
        Rsigned_2, electrodes_final, power_left_2, power_right_2 = Reorder_Rsquare(Rsigned, electrodes_orig, power_left, power_right)

        self.Features.electrodes_orig = electrodes_orig
        self.Features.power_right = power_right_2
        self.Features.power_left = power_left_2
        self.Features.time_left = time_left
        self.Features.time_right = time_right
        self.Features.time_length = time_length
        self.Features.freqs_left = freqs_left
        self.Features.electrodes_final = electrodes_final
        self.Features.Rsigned = Rsigned_2


    def initialWindow(self):
        self.btn_load_files.clicked.connect(lambda: self.load_files(self.path1.text(), self.path2.text()))
        self.btn_r2map.setEnabled(False)
        self.btn_timefreq.setEnabled(False)
        self.btn_psd.setEnabled(False)
        self.btn_topo.setEnabled(False)
        self.btn_psd_r2.setEnabled(False)
        self.btn_addPair.setEnabled(False)
        self.btn_removePair.setEnabled(False)
        self.btn_selectFeatures.setEnabled(False)
        self.selectedFeats[0].setEnabled(False)
        self.show()

    def plotWindow(self):

        fres = 1
        fmin = 0
        fs = self.PipelineParams.fSampling

        self.btn_r2map.clicked.connect(lambda: self.btnR2(fres, fmin))
        self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq(fres, fmin))
        self.btn_psd.clicked.connect(lambda: self.btnPsd(fres, fmin))
        self.btn_topo.clicked.connect(lambda: self.btnTopo(fres, fs))
        self.btn_addPair.clicked.connect(lambda: self.btnAddPair())
        self.btn_removePair.clicked.connect(lambda: self.btnRemovePair())
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())
        self.btn_psd_r2.clicked.connect(lambda: self.btnpsdR2(fres, fmin))

        self.btn_load_files.setEnabled(False)
        self.btn_r2map.setEnabled(True)
        self.btn_timefreq.setEnabled(True)
        self.btn_psd.setEnabled(True)
        self.btn_topo.setEnabled(True)
        self.btn_addPair.setEnabled(True)
        self.btn_removePair.setEnabled(True)
        self.selectedFeats[0].setEnabled(True)
        self.btn_selectFeatures.setEnabled(True)
        self.btn_psd_r2.setEnabled(True)

        self.show()

    def btnR2(self, fres, fmin):
        plot_stats(self.Features.Rsigned,
                   self.Features.freqs_left,
                   self.Features.electrodes_final,
                   fres, fmin, int(self.userFmax.text()))

    def btnTimeFreq(self, fres, fmin):
        print("TimeFreq for electrode: " + self.electrodePsd.text())
        qt_plot_tf(self.Features.time_right, self.Features.time_left,
                   self.Features.time_length, self.Features.freqs_left,
                   self.Features.electrodes_final, self.electrodePsd.text(), fres, fmin, int(self.userFmax.text()))

    def btnPsd(self, fres, fmin):
        qt_plot_psd(self.Features.power_right, self.Features.power_left,
                    self.Features.freqs_left, self.Features.electrodes_final,
                    self.electrodePsd.text(),
                    fres, fmin, int(self.userFmax.text()))

    def btnpsdR2(self, fres, fmin):
        qt_plot_psd_r2(self.Features.Rsigned,
                       self.Features.power_right, self.Features.power_left,
                       self.Features.freqs_left, self.Features.electrodes_final,
                       self.electrodePsd.text(),
                       fres, fmin, int(self.userFmax.text()))

    def btnTopo(self, fres, fs):
        print("Freq Topo: " + self.freqTopo.text())
        qt_plot_topo(self.Features.Rsigned, self.Features.electrodes_final,
                     int(self.freqTopo.text()), fres, fs)

    def btnAddPair(self):
        self.selectedFeats.append(QLineEdit())
        self.selectedFeats[-1].setText('')
        self.formLayoutOutput.addRow("Selected Feats Pair", self.selectedFeats[-1])

    def btnRemovePair(self):
        if len(self.selectedFeats) > 1:
            result = self.formLayoutOutput.getWidgetPosition(self.selectedFeats[-1])
            self.formLayoutOutput.removeRow(result[0])
            self.selectedFeats.pop()

    def btnSelectFeatures(self):
        selectedFeats = []
        for idx, feat in enumerate(self.selectedFeats):
            if feat.text() == "":
                msg = QMessageBox()
                msg.setText("Pair "+str(idx+1)+" is empty...")
                msg.exec_()
                return
            selectedFeats.append(feat.text().split(";"))
            print(feat)

        # TODO : get correct scenario filename
        scenName = 'sc2-train.xml'
        sep = "/"
        if os.name == 'nt':
            sep = "\\"
        fullScenPath = os.getcwd() + sep + "generated" + sep + scenName

        # TODO : create new function "modifyscenario", creating "branches" of pipelines
        # modifyScenario(parameterList, fullScenPath)

        textGoodbye = "Your training scenario using\n\n"
        for i in range(len(selectedFeats)):
            textGoodbye = str(textGoodbye +"  Channel " + str(selectedFeats[i][0]) + " at " + str(selectedFeats[i][1])+ " Hz\n")
        textGoodbye = str(textGoodbye + "\n... has been generated under:\n\n" + str(fullScenPath))

        msg = QMessageBox()
        msg.setText(textGoodbye)
        msg.exec_()
        exit(0)


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
        msg.setText("No Electrode with this name found")
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
        msg.setText("No Electrode with this name found")
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
        msg.setText("No Electrode with this name found")
        msg.exec_()
    else:
        time_frequency_map_between_cond(timefreq_right, time_left, freqs_left, electrodeIdx,
                                        fmin, fmax, fres, 10, timefreq_left, electrodesList)
        plt.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

