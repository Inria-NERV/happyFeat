import sys
import os
import subprocess
from multiprocessing import Process
import json
from threading import Thread

from PySide2 import QtCore
from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QListWidget
from PySide2.QtWidgets import QLineEdit
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QFileDialog
from PySide2.QtWidgets import QDialog
from PySide2.QtWidgets import QPushButton
from PySide2.QtWidgets import QInputDialog
from PySide2.QtGui import QFont

import happyfeat.lib.workspaceMgmt as workspaceMgmt
from happyfeat.lib.workspaceMgmt import *
from happyfeat. lib.utils import *

import happyfeat.bcipipeline_setup as bciSetup
import happyfeat.featureExtractionInterface as featExtractApp

# Main class
class Dialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.workspacesFolder = None
        self.workspaceExtension = ".hfw"
        self.selectedWorkspace = None
        self.launchAcqGui = False
        self.launchMainGui = False

        # TODO : check if version in config.json is the same as the software's !
        # TODO WARNING: this works with Windows only, find a way for linux
        self.userConfig = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        print(self.userConfig)
        if not os.path.exists(self.userConfig):
            with open(self.userConfig, "a+") as newfile:
                dict = {"HappyFeatVersion": "0.2.1"}
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
        selectedFolder = QFileDialog.getExistingDirectory(self, "Select directory", str(directory), QFileDialog.ShowDirsOnly)
        if selectedFolder != "":
            self.workspacesFolder = selectedFolder
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
                    if workDict["HappyFeatVersion"] != "0.2.1":
                        textWarning = "Warning: Workspace was created using an older version of HappyFeat!"
                        textWarning += "\nThis may result in unexpected behaviours. Do you want to continue?"
                        retVal = myOkCancelBox(textWarning)
                        if retVal == QMessageBox.Cancel:
                            return

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


def main():
    app = QApplication(sys.argv)
    dlg = Dialog()
    result = dlg.exec()
    if not result:
        sys.exit(-1)
    else:
        if dlg.getLaunchAcqQui():
            # Launch acquisition parameters interface (which will load the main
            # offline interface later)
            workspace = dlg.getSelectedWorkspace()
            p = Process(target=bciSetup.launch, args=(str(sys.argv[0]), workspace))
            p.start()
            p.join()

        if dlg.getLaunchMainQui():
            # Launch main offline extraction interface
            workspace = dlg.getSelectedWorkspace()
            p = Process(target=featExtractApp.launch, args=(str(sys.argv[0]), workspace))
            p.start()
            p.join()


# main entry point
if __name__ == '__main__':
    main()
    sys.exit(0)
