import sys
import os
import subprocess
import json
from threading import Thread

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtGui import QFont

import workspaceMgmt
from workspaceMgmt import *
from utils import *

# Main class
class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.workspacesFolder = None
        self.workspaceExtension = ".hfw"
        self.selectedWorkspace = None
        self.launchAcqGui = False
        self.launchMainGui = False

        # TODO WARNING: this works with Windows only, find a way for linux
        self.userConfig = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        if not os.path.exists(self.userConfig):
            with open(self.userConfig, "a+") as newfile:
                dict = {"HappyFeatVersion": "0.0"}
                json.dump(dict, newfile, indent=4)

        with open(self.userConfig, "r+") as userCfg:
            currentCfg = json.load(userCfg)
            if "lastWorkspacePath" in currentCfg:
                self.workspacesFolder = currentCfg["lastWorkspacePath"]

        # INTERFACE INIT...
        self.setWindowTitle('HappyFeat - Select workspace')
        self.dlgLayout = QVBoxLayout()

        label = str("=== Welcome to HappyFeat! ===")
        self.label = QLabel(label)
        self.label.setFont(QFont("system-ui", 12))
        self.label.setAlignment(QtCore.Qt.AlignCenter)

        # Workspace folder selection
        self.labelWs = QLabel()
        self.labelWs.setText(str("Workspaces folder"))
        self.labelWs.setAlignment(QtCore.Qt.AlignCenter)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(lambda: self.browseForWsFolder())
        self.WsWidget = QWidget()
        self.layout_h = QHBoxLayout(self.WsWidget)
        self.WsTextBox = QLineEdit()
        self.WsTextBox.setText("")
        if self.workspacesFolder:
            self.WsTextBox.setText(self.workspacesFolder)
        self.WsTextBox.setEnabled(False)
        self.layout_h.addWidget(self.WsTextBox)
        self.layout_h.addWidget(self.btn_browse)

        # Buttons
        self.btn_newSession = QPushButton("Start new workspace")
        self.btn_newSession.clicked.connect(lambda: self.startNewWorkspace())
        self.btn_loadSession = QPushButton("Load an existing workspace")
        self.btn_loadSession.clicked.connect(lambda: self.loadExistingWorkspace())

        self.workspaceListWidget = QListWidget()
        self.workspaceListWidget.setSelectionMode(QListWidget.SingleSelection)

        self.dlgLayout.addWidget(self.label)
        self.dlgLayout.addWidget(self.labelWs)
        self.dlgLayout.addWidget(self.WsWidget)
        self.dlgLayout.addWidget(self.btn_newSession)
        self.dlgLayout.addWidget(self.btn_loadSession)
        self.dlgLayout.addWidget(self.workspaceListWidget)

        self.setLayout(self.dlgLayout)

        # Update List...
        self.updateWorkspaceList()

        # display initial layout
        self.displayWindow()

    def displayWindow(self):
        self.show()

    def browseForWsFolder(self):
        directory = os.getcwd()
        self.workspacesFolder = QFileDialog.getExistingDirectory(self, "Select directory", str(directory), QFileDialog.ShowDirsOnly)
        self.WsTextBox.setText(self.workspacesFolder)
        self.updateWorkspaceList()
        workspaceMgmt.setKeyValue(self.userConfig, "lastWorkspacePath", self.workspacesFolder)
        return

    def updateWorkspaceList(self):
        workspaceList = []
        self.workspaceListWidget.clear()
        for workspaceName in os.listdir(self.workspacesFolder):
            if workspaceName.endswith(".hfw"):
                workspaceList.append(workspaceName)
                self.workspaceListWidget.addItem(workspaceList[-1])

    def loadExistingWorkspace(self):
        if not self.workspaceListWidget.selectedItems():
            myMsgBox("Please select a workspace...")
            return

        chosenWorkspace = self.workspaceListWidget.selectedItems()[0].text()
        if not chosenWorkspace:
            myMsgBox("Please select a workspace...")
            return

        fullWorkspacePath = os.path.join(self.workspacesFolder, chosenWorkspace)

        # Check that all folders have been created (at least for "1")
        validWs = False
        with open(fullWorkspacePath, "r") as wp:
            workDict = json.load(wp)
            if workDict:
                if "HappyFeatVersion" in workDict:
                    pathToCheck = os.path.join(self.workspacesFolder, os.path.splitext(chosenWorkspace)[0])
                    if os.path.exists(pathToCheck):
                        pathToCheck1 = os.path.join(pathToCheck, "signals")
                        pathToCheck2 = os.path.join(pathToCheck, "sessions")
                        if os.path.exists(pathToCheck1) and os.path.exists(pathToCheck2):
                            pathToCheck2 = os.path.join(pathToCheck2, "1")
                            if os.path.exists(pathToCheck2):
                                pathToCheck1 = os.path.join(pathToCheck2, "extract")
                                pathToCheck2 = os.path.join(pathToCheck2, "train")
                                if os.path.exists(pathToCheck1) and os.path.exists(pathToCheck2):
                                    validWs = True
        
        if not validWs:
            myMsgBox("Selected workspace is invalid.\nPlease make sure all subfolders exist...")
            return

        self.selectedWorkspace = fullWorkspacePath
        self.launchMainGui = True
        self.accept()

    def startNewWorkspace(self):
        # Check that a top Workspace folder has been selected
        if not self.workspacesFolder:
            myMsgBox("Please select a \"top\" Workspace folder to create your workspace into.")
            return

        # Prompt user for filename, using QInputDialog
        workspaceName, ok = QInputDialog.getText(self, 'New workspace', 'Enter a name for the new workspace:')
        if not ok:
            return
        else:
            # Check if file already exists, and prompt user for overwrite
            fullWorkspacePath = os.path.join(self.workspacesFolder, str(workspaceName+self.workspaceExtension))
            if os.path.exists(fullWorkspacePath):
                retVal = myOkCancelBox("Workspace already exists! Overwrite config file?\n(Folders and files will NOT be erased)")
                if not retVal == QMessageBox.Ok:
                    # just exit and let the user start again
                    return

            # Initialize a workspace file in the workspace folder
            initializeNewWorkspace(fullWorkspacePath)
            self.selectedWorkspace = fullWorkspacePath

            # Create folder tree for new workspace
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName)):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName))
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName, "signals")):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName, "signals"))
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName, "sessions")):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName, "sessions"))
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1")):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1"))
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1", "extract")):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1", "extract"))
            if not os.path.exists(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1", "train")):
                os.mkdir(os.path.join(self.workspacesFolder, workspaceName, "sessions", "1", "train"))
            # Launch GUI 1 (metric and acquisition parameters)
            self.launchAcqGui = True
            self.accept()

    # Getters...
    def getSelectedWorkspace(self):
        return self.selectedWorkspace

    def getLaunchAcqQui(self):
        return self.launchAcqGui

    def getLaunchMainQui(self):
        return self.launchMainGui


def launchThread(script, space):
    p = subprocess.Popen(["python", script, space],
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


# main entry point
if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = Dialog()
    result = dlg.exec()
    if not result:
        sys.exit(-1)
    else:
        if dlg.getLaunchAcqQui():
            # Launch acquisition parameters interface (which will load the main
            # offline interface later)
            pyscript = "1-bcipipeline_qt.py"
            workspace = dlg.getSelectedWorkspace()
            threadAcqGui = Thread(target=launchThread, args=(pyscript, workspace))
            threadAcqGui.start()
            threadAcqGui.join()

        if dlg.getLaunchMainQui():
            # Launch main offline extraction interface
            pyscript = "2-featureExtractionInterface.py"
            workspace = dlg.getSelectedWorkspace()
            threadAcqGui = Thread(target=launchThread, args=(pyscript, workspace))
            threadAcqGui.start()
            threadAcqGui.join()

        sys.exit(0)
