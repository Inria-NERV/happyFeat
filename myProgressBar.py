from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QBasicTimer, QThread, pyqtSignal

import sys

class ProgressBar(QDialog):

    def __init__(self, label, nbIncrements, parent=None):

        super().__init__(parent)

        self.nbIncrements = nbIncrements
        self.label = label
        self.resize(800, 150)
        self.setWindowTitle("Processing...")

        self.currentProgress = 0

        self.featProgressBar = QProgressBar(self)
        self.featProgressBar.setTextVisible(True)
        self.featProgressBar.setMinimum(0)
        self.featProgressBar.setMaximum(nbIncrements)
        self.featProgressBar.setValue(0)
        self.featProgressBar.setFormat(self.label + " : " + str(self.currentProgress) + "/" + str(self.nbIncrements))

        layout = QVBoxLayout()
        layout.addWidget(self.featProgressBar)
        self.setLayout(layout)
        self.show()

    def increment(self):
        self.currentProgress += 1
        self.featProgressBar.setValue(self.currentProgress)
        self.featProgressBar.setFormat(self.label + " : " + str(self.currentProgress) + "/" + str(self.nbIncrements))

    def changeLabel(self, newLabel):
        self.label = newLabel
        self.featProgressBar.setFormat(self.label + " : " + str(self.currentProgress) + "/" + str(self.nbIncrements))

    def finish(self):
        self.close()

    def showBar(self):
        self.show()

class ProgressBarNoInfo(QDialog):

    def __init__(self, label, parent=None):

        super().__init__(parent)

        self.resize(350, 100)
        self.setWindowTitle("Processing...")

        self.tipLabel = QLabel(label)

        self.featProgressBar = QProgressBar(self)
        self.featProgressBar.setRange(0, 0)

        tipLayout = QHBoxLayout()
        tipLayout.addWidget(self.tipLabel)

        featLayout = QHBoxLayout()
        featLayout.addWidget(self.featProgressBar)

        layout = QVBoxLayout()
        layout.addLayout(featLayout)
        layout.addLayout(tipLayout)
        self.setLayout(layout)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    label = "Extracting features"
    filenum = 10
    progress = ProgressBar(label, filenum)
    progress.show()
    app.exec_()
