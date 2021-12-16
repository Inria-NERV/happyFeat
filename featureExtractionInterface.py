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
    electrodes = []
    elec_2 = []
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
        self.btn_extract = QPushButton("Extract Features")
        self.btn_r2map = QPushButton("Plot R2Map")
        self.btn_timefreq = QPushButton("Plot Time/Freq Analysis")
        self.btn_psd = QPushButton("Plot PSD for Spec. Freq.")
        self.btn_topo = QPushButton("Plot Topography for Spec. Freq.")
        self.btn_psd_r2 = QPushButton("Plot R2 and PSD")

        # FEATURE SELECTION PART
        self.label2 = QLabel('----- SELECT FEATURES FOR TRAINING -----')
        self.label2.setAlignment(QtCore.Qt.AlignCenter)

        self.formLayoutOutput = QFormLayout()
        # Param Output 1 : Selected Channels / Electrodes
        self.selectedChans = QLineEdit()
        self.selectedChans.setText('')
        chanText = 'ELECTRODES TO SELECT\n(separated with \";\")'
        chanText = str(chanText+"\n  ex: FC1;FC2;CP4")
        self.formLayoutOutput.addRow(chanText, self.selectedChans)
        # Param Output 2 : Selected Frequencies
        self.selectedFreqs = QLineEdit()
        self.selectedFreqs.setText('')
        freqText = 'FREQUENCIES TO SELECT\n(freqs or ranges separated with \";\")'
        freqText = str(freqText+"\n  ex: 14:22;24;26:32")
        self.formLayoutOutput.addRow(freqText, self.selectedFreqs)

        self.btn_selectFeatures = QPushButton("Select features & generate scenarios")

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addLayout(self.formLayout)
        self.dlgLayout.addWidget(self.btn_load_files)
        self.dlgLayout.addWidget(self.btn_extract)
        self.dlgLayout.addWidget(self.btn_r2map)
        self.dlgLayout.addWidget(self.btn_timefreq)
        self.dlgLayout.addWidget(self.btn_psd)
        self.dlgLayout.addWidget(self.btn_topo)
        self.dlgLayout.addWidget(self.btn_psd_r2)
        self.dlgLayout.addWidget(self.label2)
        self.dlgLayout.addLayout(self.formLayoutOutput)
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
            self.extractWindow()

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
        electrodes = channel_generator(nbElectrodes, 'TP9', 'TP10')
        freqs_left = np.arange(0, n_bins)
        Rsigned = Compute_Rsquare_Map_Welch(power_right[:, :, :250], power_left[:, :, :250])
        print("INITIAL RSQUARE")
        for i in range(10):
            print(Rsigned[i, :5])
        Rsigned_2, electrodes, power_left_2, power_right_2 = Reorder_Rsquare(Rsigned, electrodes, power_left, power_right)

        print("FINAL RSQUARE")
        for i in range(10):
            print(Rsigned_2[i, :5])

        self.Features.elec_2 = electrodes
        self.Features.power_right = power_right_2
        self.Features.power_left = power_left_2
        self.Features.time_left = time_left
        self.Features.time_right = time_right
        self.Features.time_length = time_length
        self.Features.freqs_left = freqs_left
        self.Features.electrodes = electrodes
        self.Features.Rsigned = Rsigned_2

        # CHANGING WINDOW TO "PLOT" LAYOUT
        self.plotWindow()

    def initialWindow(self):
        self.btn_load_files.clicked.connect(lambda: self.load_files(self.path1.text(), self.path2.text()))
        self.btn_extract.setEnabled(False)
        self.btn_r2map.setEnabled(False)
        self.btn_timefreq.setEnabled(False)
        self.btn_psd.setEnabled(False)
        self.btn_topo.setEnabled(False)
        self.btn_psd_r2.setEnabled(False)
        self.btn_selectFeatures.setEnabled(False)
        self.show()

    def extractWindow(self):
        self.btn_extract.clicked.connect(lambda: self.extract_features())
        self.btn_load_files.setEnabled(False)
        self.btn_extract.setEnabled(True)
        self.show()

    def plotWindow(self):

        electrode = self.electrodePsd.text()
        frequency = int(self.freqTopo.text())
        fres = 1
        fmin = 0
        fs = self.PipelineParams.fSampling

        self.btn_r2map.clicked.connect(lambda: self.btnR2(fres, fmin))
        self.btn_timefreq.clicked.connect(lambda: self.btnTimeFreq(fres, fmin))
        self.btn_psd.clicked.connect(lambda: self.btnPsd(fres, fmin))
        self.btn_topo.clicked.connect(lambda: self.btnTopo(fres, fs))
        self.btn_selectFeatures.clicked.connect(lambda: self.btnSelectFeatures())
        self.btn_psd_r2.clicked.connect(lambda: self.btnpsdR2(fres, fmin))

        self.btn_r2map.setEnabled(True)
        self.btn_timefreq.setEnabled(True)
        self.btn_psd.setEnabled(True)
        self.btn_topo.setEnabled(True)
        self.btn_selectFeatures.setEnabled(True)
        self.btn_psd_r2.setEnabled(True)

        self.show()

    def btnR2(self, fres, fmin):
        plot_stats(self.Features.Rsigned,
                   self.Features.freqs_left,
                   self.Features.elec_2,
                   fres, fmin, int(self.userFmax.text()))

    def btnTimeFreq(self, fres, fmin):
        print("TimeFreq for electrode: " + self.electrodePsd.text())
        qt_plot_tf(self.Features.time_right, self.Features.time_left,
                   self.Features.time_length, self.Features.freqs_left,
                   self.Features.electrodes, self.electrodePsd.text(), fres, fmin, int(self.userFmax.text()))

    def btnPsd(self, fres, fmin):
        print("PSD for electrode: " + self.electrodePsd.text())
        qt_plot_psd(self.Features.power_right, self.Features.power_left,
                    self.Features.freqs_left, self.Features.elec_2,
                    self.electrodePsd.text(),
                    fres, fmin, int(self.userFmax.text()))

    def btnpsdR2(self, fres, fmin):
        qt_plot_psd_r2(self.Features.Rsigned,
                       self.Features.power_right, self.Features.power_left,
                       self.Features.freqs_left, self.Features.elec_2,
                       self.electrodePsd.text(),
                       fres, fmin, int(self.userFmax.text()))


    def btnTopo(self, fres, fs):
        print("Freq Topo: " + self.freqTopo.text())
        qt_plot_topo(self.Features.Rsigned, self.Features.electrodes,
                     int(self.freqTopo.text()), fres, fs)

    def btnSelectFeatures(self):
        # TODO : get correct scenario filename
        scenName = 'sc2-train.xml'
        sep = "/"
        if os.name == 'nt':
            sep = "\\"
        fullScenPath = os.getcwd() + sep + "generated" + sep + scenName

        # TODO : Reformat selectedElectrodes & selectedFrequencies to fit...
        selectedElectrodes = self.selectedChans.text()
        selectedFrequencies = self.selectedFreqs.text()
        parameterList = [["Electrodes", selectedElectrodes], ["Frequencies", selectedFrequencies]]

        modifyScenario(parameterList, fullScenPath)

        msg = QMessageBox()
        msg.setText("Your training scenario using\n\n"
                    + "frequencies " + selectedFrequencies + " Hz\n"
                    + "and channels " + selectedElectrodes + "\n\n"
                    + "has been generated under:\n\n"
                    + str(fullScenPath))
        msg.exec_()
        exit(0)


def plot_stats(Rsigned, freqs_left, electrodes, fres, fmin, fmax):
    smoothing  = False
    plot_Rsquare_calcul_welch(Rsigned,np.array(electrodes)[:], freqs_left, smoothing, fres, 10, fmin, fmax)
    plt.show()

def qt_plot_psd_r2(Rsigned, power_right, power_left, freqs_left, electrodes, electrode, fres, fmin, fmax):
    electrodeExists = False
    electrodeIdx = 0
    for i in range(len(electrodes)):
        if electrodes[i] == electrode:
            electrodeIdx = i
            electrodeExists = True
    if not electrodeExists:
        msg = QMessageBox()
        msg.setText("No Electrode with this name found")
        msg.exec_()
    else:
        plot_psd2(Rsigned, power_right, power_left, freqs_left, electrodeIdx, electrodes, 10, fmin, fmax, fres)
        plt.show()

def qt_plot_psd(power_right, power_left, freqs_left, electrodes, electrode, fres, fmin, fmax):
    electrodeExists = False
    electrodeIdx = 0
    for i in range(len(electrodes)):
        if electrodes[i] == electrode:
            electrodeIdx = i
            electrodeExists = True
    if not electrodeExists:
        msg = QMessageBox()
        msg.setText("No Electrode with this name found")
        msg.exec_()
    else:
        plot_psd(power_right, power_left, freqs_left, electrodeIdx, electrodes, 10, fmin, fmax, fres)
        plt.show()


def qt_plot_topo(Rsigned, electrodes, frequency, fres, fs):
    topo_plot(Rsigned, round(frequency/fres), electrodes, fres, fs, 'Signed R square')
    plt.show()


def qt_plot_tf(timefreq_right, timefreq_left, time_left, freqs_left, electrodes, electrode, fres, fmin, fmax):
    smoothing  = False
    electrodeExists = False
    electrodeIdx = 0
    for i in range(len(electrodes)):
        if electrodes[i] == electrode:
            electrodeIdx = i
            electrodeExists = True

    if not electrodeExists:
        msg = QMessageBox()
        msg.setText("No Electrode with this name found")
        msg.exec_()
    else:
        time_frequency_map_between_cond(timefreq_right, time_left, freqs_left, electrodeIdx,
                                        fmin, fmax, fres, 10, timefreq_left, electrodes)
        plt.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    dlg = Dialog()
    sys.exit(app.exec_())

