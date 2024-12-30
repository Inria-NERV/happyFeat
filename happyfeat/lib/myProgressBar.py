from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QProgressBar
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QBasicTimer, QThread, Signal

import sys

class ProgressBar(QDialog):

    def __init__(self, title, label, nbIncrements, parent=None):

        super().__init__(parent)

        self.nbIncrements = nbIncrements
        self.resize(800, 150)
        self.setWindowTitle(title)
        self.currentProgress = 0

        self.label = QLabel(self)
        self.label.setText(label)
        self.label.setAlignment(Qt.AlignCenter)

        self.featProgressBar = QProgressBar(self)
        self.featProgressBar.setTextVisible(True)
        self.featProgressBar.setMinimum(0)
        self.featProgressBar.setMaximum(nbIncrements)
        self.featProgressBar.setValue(0)
        self.featProgressBar.setFormat(str(self.currentProgress) + "/" + str(self.nbIncrements))

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.featProgressBar)
        self.setLayout(layout)
        self.show()

    def increment(self):
        self.currentProgress += 1
        self.featProgressBar.setValue(self.currentProgress)
        self.featProgressBar.setFormat(str(self.currentProgress) + "/" + str(self.nbIncrements))

    def changeLabel(self, newLabel):
        self.label.setText(newLabel)

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
