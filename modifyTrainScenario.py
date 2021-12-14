# --
# modifyTrainScenario.py
# --
# Launched from OpenViBE at the end of sc2-extract-select.xml ,
# when the spectra have been computed. This script computes the
# wanted visualization (depending on the ran command, which itself
# is modified by the generation script bcipipeline_script.py), then
# prompts the user to select some features (e.g. Electrodes, frequencies...)
#
# From those parameters, the training scenario (sc2-train.xml) is modified
# --

import xml.etree.ElementTree as ET
import os
# import bcipipeline_settings as settings
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt
import numpy as np

from DataAnalysis import *
from DataVisualization import *

class PromptGui:

    def __init__(self, root):

        self.window = root

        self.title = tk.Label(text="Good news, BCI user! Your data is ready."
                                   "\nPlease select a set of features."
                                   "\nUse \";\" for multiple options, and \":\" for range (eg frequency band)",
                              height=6)
        self.button = tk.Button(text="All good", command=self.modifyTrainScenario)

        self.parameterGuiLabelList = []
        self.parameterGuiEntryList = []

        self.rowNb = 1

    def run(self):
        self.title.grid(row=self.rowNb, column=1)
        self.rowNb += 1
        self.displayParameters()
        self.button.grid(row=self.rowNb, column=1, padx=2, pady=2)
        # self.window.mainloop()

    def displayParameters(self):
        ###
        # NOTE / TODO : make that automatized, reading from some sort of config file...
        ###

        labeltext1 = tk.StringVar()
        text1 = "Frequencies"
        labeltext1.set(text1)
        label1 = tk.Label(textvariable=labeltext1)
        label1.grid(row=self.rowNb, column=1)
        param1 = tk.StringVar(value="3:80")
        entry1 = tk.Entry(textvariable=param1, width=30)
        entry1.grid(row=self.rowNb, column=2)

        self.rowNb+=1
        self.parameterGuiLabelList.append(label1)
        self.parameterGuiEntryList.append(entry1)

        labeltext2 = tk.StringVar()
        text2 = "Electrodes"
        labeltext2.set(text2)
        label2 = tk.Label(textvariable=labeltext2)
        label2.grid(row=self.rowNb, column=1)
        param2 = tk.StringVar(value="Cz;C2;C4;C6;C8")
        entry2 = tk.Entry(textvariable=param2, width=30)
        entry2.grid(row=self.rowNb, column=2)

        self.rowNb+=1
        self.parameterGuiLabelList.append(label2)
        self.parameterGuiEntryList.append(entry2)

    def modifyTrainScenario(self):
        parameterList = []
        for i in range(len(self.parameterGuiEntryList)):
            # List of parameters is a list of pairs (text, parameters-as-string)
            parameterList.append( (self.parameterGuiLabelList[i].cget("text") ,
                                   self.parameterGuiEntryList[i].get()) )
            print("Parameter ", i, " : (", self.parameterGuiLabelList[i].cget("text"),
                  " , ", self.parameterGuiEntryList[i].get(), ")")

        modifyScenario(parameterList)

        # Erase the previous displays
        for parameter in self.window.grid_slaves():
            parameter.grid_remove()

        text = "Thanks for using this script!\nYour train scenario is ready."
        text += "\n\nDon't forget to double check...\nYou can now close this window."
        label = tk.Label(text=text, height=8)
        label.grid(row=1)

        self.button = tk.Button(self.window, text="Close", command=self.closeWindow)
        self.button.grid(row=2, padx=2, pady=2)

    def closeWindow(self):
        self.window.destroy()


def modifyScenario(parameterList):
    print("MODIFYING SCENARIO!")

    # First, parse the parameters list...
    # TODO :
    # For now the two parameters are set (frequencies and electrodes)
    # but in the long run they'll have to be parametrized

    frequencies = []
    electrodes = []

    # List of parameters is a list of pairs (text, parameters-as-string)
    for parameter in parameterList:
        parameterLabel = parameter[0]
        parameterString = parameter[1]
        print("Parameter ", parameterLabel, " : ", parameterString)
        if parameterLabel == "Frequencies":
            # Frequencies
            frequencies = parameterString
        elif parameterLabel == "Electrodes":
            # Electrodes
            electrodes = parameterString

    # OPEN THE XML SCENARIO FILE TO MODIFY
    xmlFileName = "sc2-train.xml"
    sep = "/"
    if os.name == 'nt':
        sep = "\\"

    xmlPath = os.getcwd() + sep + "generated" + sep + xmlFileName

    tree = ET.parse(xmlPath)
    root = tree.getroot()

    # PROTOTYPE : Find "Frequency Band Selector" / "Channel Selector"
    # and modify them
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            for name in box.findall('Name'):

                if name.text == "Frequency Band Selector":
                    # TODO : SELECTION could be done on box identifier instead
                    print("- BOX ", name.text)
                    for setting in box.find('Settings').findall('Setting'):
                        if setting.find('Name').text == "Frequencies to select":
                            value = setting.find('Value')
                            print("-- ORIGINAL VALUE ", value.text)
                            value.text = frequencies
                            value.set('updated', 'yes')
                            print("--- UPDATED VALUE ", value.text)

                elif name.text == "Channel Selector":
                    # TODO : SELECTION could be done on box identifier instead
                    print("- BOX ", name.text)
                    for setting in box.find('Settings').findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            value = setting.find('Value')
                            print("-- ORIGINAL VALUE ", value.text)
                            value.text = electrodes
                            value.set('updated', 'yes')
                            print("--- UPDATED VALUE ", value.text)

    tree.write(xmlPath)


def main():
    print("Coucou")

    # DO STUFF BEFORE RUNNING THE GUI
    # LIKE COMPUTING THE R2 MAP OR OTHER VIZZZ
    # ...
    # ...
    # DUMMY HEATMAP FOR NOW

    root = tk.Tk()

    a = np.random.random((128, 128))
    plt.imshow(a, cmap='hot', interpolation='nearest')
    plt.pause(0.001)

    # OPEN GUI AND ASK USER TO SELECT FEATURES
    gui = PromptGui(root)
    gui.run()

    plt.show()


if __name__ == "__main__":
    main()