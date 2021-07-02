import tkinter as tk
from generateOpenVibeScenario import *
import os
import bcipipeline_settings as settings


class Interface:

    def __init__(self):

        self.options = settings.options
        self.optionsNbParams = settings.optionsNbParams

        self.window = tk.Tk()
        self.title = tk.Label(text="Welcome, BCI user! What experiment would you like to prepare?",height=2)
        self.button = tk.Button(self.window, text="Generate", command=self.generate)

        self.bciScenType = tk.StringVar(self.window)
        self.bciScenType.set(self.options[0])  # default value
        self.optionMenu = tk.OptionMenu(self.window, self.bciScenType, *self.options, command=self.updateOptions)

        self.parameterGuiLabelList = []
        self.parameterGuiEntryList = []

    def run(self):
        self.title.grid(row=1, column=1)
        self.optionMenu.grid(row=2, column=1)
        self.window.mainloop()

    def updateOptions(self, choice):
        choice = self.bciScenType.get()
        if choice == self.options[0]:
            return

        choicetext = "You have chosen " + choice + "\nEnter your parameters and click \"Generate\" to continue..."
        message = tk.Label(text=choicetext, height=2)

        # Erase the previous displays
        for parameter in self.window.grid_slaves():
            if int(parameter.grid_info()["row"]) >= 3:
                parameter.grid_remove()

        # Print useless message, show button
        message.grid(row=3, column=1)
        self.button.grid(row=4, column=1)

        # Reinit the lists
        self.parameterGuiLabelList = []
        self.parameterGuiEntryList = []

        # Update the parameter options in the display
        self.displayParameters(choice)

    def displayParameters(self, choice):
        ###
        # NOTE / TODO : make that automatized, reading from some sort of config file...
        ###
        currentrow = 5

        # Power spectrum
        if choice == self.options[1]:
            for i in range(0, self.optionsNbParams[1]):
                labelText = tk.StringVar()
                text = "Spectral power param " + str(i)
                labelText.set(text)
                # GET ACTUAL PARAM NAME SOMEHOW
                label = tk.Label(textvariable=labelText)
                label.grid(row=currentrow, column=1)
                param = tk.StringVar(None)
                entry = tk.Entry(textvariable=param, width=30)
                entry.grid(row=currentrow, column=2)

                self.parameterGuiLabelList.append(label)
                self.parameterGuiEntryList.append(entry)

                currentrow += 1
        # Functional Connectivity
        elif choice == self.options[2]:
            for i in range(0, self.optionsNbParams[2]):
                labelText = tk.StringVar()
                text = "Functional Connectivity param " + str(i)
                labelText.set(text)
                # GET ACTUAL PARAM NAME SOMEHOW
                label = tk.Label(textvariable=labelText)
                label.grid(row=currentrow, column=1)
                param = tk.StringVar(None)
                entry = tk.Entry(textvariable=param, width=30)
                entry.grid(row=currentrow, column=2)

                self.parameterGuiLabelList.append(label)
                self.parameterGuiEntryList.append(entry)

                currentrow += 1

    def generate(self):
        parameterList = []
        for i in range(len(self.parameterGuiEntryList)):
            parameterList.append(self.parameterGuiEntryList[i].get())
            print("Parameter ", i, " : ", self.parameterGuiEntryList[i].get())

        generateScenarios(self.bciScenType.get(), parameterList)

        # Erase the previous displays
        for parameter in self.window.grid_slaves():
            parameter.grid_remove()

        text = "Thanks for using the generation script!\nYour files are in " + os.getcwd() + "/generated/"
        text += "\n\nDon't forget to double check the generated scenarios...!\nYou can now close this window."
        labelText = tk.StringVar()
        labelText.set(text)
        label = tk.Label(textvariable=labelText)
        label.grid(row=1, column=1)

        self.button = tk.Button(self.window, text="Close", command=self.closeWindow)
        self.button.grid(row=2, column=1)

    def closeWindow(self):
        self.window.destroy()

def main():
    interface = Interface()
    interface.run()


if __name__ == "__main__":
    main()
