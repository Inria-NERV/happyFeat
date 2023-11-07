from itertools import chain, combinations
from PySide2.QtWidgets import QMessageBox

def myPowerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(1, len(s)+1))

def myMsgBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.exec_()
    return

def myOkCancelBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    returnVal = msg.exec_()
    return returnVal

def myYesNoToAllBox(text):
    msg = QMessageBox()
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No | QMessageBox.NoToAll)
    returnVal = msg.exec_()
    return returnVal

