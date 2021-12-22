import xml.etree.ElementTree as ET
from xml.dom import minidom
import os


def modifyScenarioGeneralSettings(scenXml, parameterDict):
    print("---Modifying " + scenXml)
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PARSE SCENARIO GENERAL SETTINGS, AND MODIFY THEM ACCORDING TO THE PROVIDED
    # PARAMETER LIST
    for settings in root.findall('Settings'):
        for setting in settings.findall('Setting'):
            for param in parameterDict:
                if param == setting.find('Name').text:
                    xmlVal = setting.find('Value')
                    xmlVal.text = parameterDict[param]

    # WRITE NEW XML
    tree.write(scenXml)

    return

def modifyAcqScenario(scenXml, parameterDict):
    print("---Modifying " + scenXml + " Graz Variables")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PARSE SCENARIO BOX SETTINGS, AND MODIFY GRAZ PROTOCOL VARIABLES
    # PARAMETER LIST
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == 'Graz Motor Imagery BCI Stimulator':
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Number of Trials for Each Class":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["TrialNb"]
                            continue
                        elif setting.find('Name').text == "Baseline Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["Baseline"]
                            continue
                        elif setting.find('Name').text == "Wait For Cue Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["TrialWait"]
                            continue
                        elif setting.find('Name').text == "Display Cue Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["TrialWait"]
                            continue
                        elif setting.find('Name').text == "End of Trial Minimum Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["EndTrial"]
                            continue
                        elif setting.find('Name').text == "End of Trial Maximum Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["EndTrial"]
                            continue

    # WRITE NEW XML
    tree.write(scenXml)

    return

def modifyTrainScenarioWithPairs(pairs, scenFullPath):

    nbPipelines = len(pairs)

    # OPEN THE XML SCENARIO FILE TO MODIFY
    # xmlFileName = "sc2-train.xml"
    scenXml = scenFullPath
    sep = "/"
    if os.name == 'nt':
        sep = "\\"

    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PROTOTYPE :
    # Step 1 : find the 2 already existing
    # "Frequency Band Selector" / "Channel Selector" boxes
    # and modify their parameters with the first Feature Pair
    print("REPLACING EXISTING  FREQUENCY / CHANNEL PAIR")
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
                            value.text = pairs[0][1]
                            print("--- UPDATED VALUE ", value.text)

                elif name.text == "Channel Selector":
                    # TODO : SELECTION could be done on box identifier instead
                    print("- BOX ", name.text)
                    for setting in box.find('Settings').findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            value = setting.find('Value')
                            print("-- ORIGINAL VALUE ", value.text)
                            value.text = pairs[0][1]
                            print("--- UPDATED VALUE ", value.text)

    # Step 2 :


    # Step 3 : write new XML
    tree.write(scenXml)


def modifyScenario(parameterList, scenarioFilename):
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
    # xmlFileName = "sc2-train.xml"
    xmlFileName = scenarioFilename
    sep = "/"
    if os.name == 'nt':
        sep = "\\"

    # xmlPath = os.getcwd() + sep + "generated" + sep + xmlFileName
    # tree = ET.parse(xmlPath)
    tree = ET.parse(xmlFileName)
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
                            print("--- UPDATED VALUE ", value.text)

                elif name.text == "Channel Selector":
                    # TODO : SELECTION could be done on box identifier instead
                    print("- BOX ", name.text)
                    for setting in box.find('Settings').findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            value = setting.find('Value')
                            print("-- ORIGINAL VALUE ", value.text)
                            value.text = electrodes
                            print("--- UPDATED VALUE ", value.text)

    tree.write(xmlFileName)