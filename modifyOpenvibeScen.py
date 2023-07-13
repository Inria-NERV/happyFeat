import copy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import binascii


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

def modifyExtractionIO(scenXml, newFilename, newOutputSpect1, newOutputSpect2, newOutputBaseline1, newOutputBaseline2, newOutputConnect1, newOutputConnect2, newOutputTrials):
    print("---Modifying " + scenXml + " input and output")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PARSE SCENARIO GENERAL SETTINGS, AND MODIFY THEM ACCORDING TO THE PROVIDED
    # PARAMETER LIST
    for settings in root.findall('Settings'):
        for setting in settings.findall('Setting'):
            if setting.find('Name').text == "EEGData":
                xmlVal = setting.find('Value')
                xmlVal.text = newFilename
            elif setting.find('Name').text == "OutputSpect1":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputSpect1
            elif setting.find('Name').text == "OutputSpect2":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputSpect2
            elif setting.find('Name').text == "OutputConnect1":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputConnect1
            elif setting.find('Name').text == "OutputConnect2":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputConnect2
            elif setting.find('Name').text == "OutputBaseline1":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputBaseline1
            elif setting.find('Name').text == "OutputBaseline2":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputBaseline2
            elif setting.find('Name').text == "OutputTrials":
                xmlVal = setting.find('Value')
                xmlVal.text = newOutputTrials

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyAcqScenario(scenXml, parameterDict, boolOnline):
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
                            xmlVal.text = parameterDict["TrialLength"]
                            continue
                        elif setting.find('Name').text == "End of Trial Minimum Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["EndTrialMin"]
                            continue
                        elif setting.find('Name').text == "End of Trial Maximum Duration (in sec)":
                            xmlVal = setting.find('Value')
                            xmlVal.text = parameterDict["EndTrialMax"]
                            continue
                        elif setting.find('Name').text == "Feedback Duration (in sec)":
                            if boolOnline:
                                xmlVal = setting.find('Value')
                                xmlVal.text = parameterDict["FeedbackLength"]
                                continue
                            else:
                                xmlVal = setting.find('Value')
                                xmlVal.text = str(0)
                                continue

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainScenario(chanFreqPairs, epochCount, scenXml):
    print("---Modifying " + scenXml + " with Selected Features")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # FIRST STEP AND
    # SIMPLEST CASE : modify existing branches in the scenario.
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):

            if box.find('Name').text == 'Channel Selector':
                print("-- CHANNEL SELECTOR BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][0]
                            print("            with " + xmlVal.text)
                            break

            if box.find('Name').text == 'Frequency Band Selector':
                print("-- FREQ SELECTION BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                        # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                        if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][1]
                            print("            with " + xmlVal.text)
                            break
            if box.find('Name').text == 'Epoch average':
                print("-- EPOCH AVERAGE BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Epoch count":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = str(epochCount)
                            print("            with " + xmlVal.text)
                            break

    if len(chanFreqPairs) > 1:
        # TOUGHEST CASE : NEED TO COPY/PASTE MULTIPLE PROCESSING
        # BRANCHES WITH CHANNEL SELECTOR, TIME EPOCH, AR COEFFS,
        # FREQ BAND SELECTOR AND SPECTRUM AVERAGE

        # FIRST STEP : GET THE TWO "SPLIT" IDENTITY BOXES
        splitBoxes = []
        splitIdx = 0
        for boxes in root.findall('Boxes'):
            for box in boxes.findall('Box'):
                if box.find('Name').text == 'SPLIT':
                    print("-- SPLIT " + str(splitIdx))
                    splitBoxes.append(box)
                    splitIdx += 1
                    continue

        # Find Id of Classifier trainer box
        boxLast = findBox(root, "Classifier trainer")
        boxLastId = boxLast.find("Identifier").text
        for box in splitBoxes:
            boxId = box.find("Identifier").text
            locOffset = 120

            # Find all chained box btw those two
            if boxId is not None and boxLastId is not None:
                boxList = findChainedBoxes(root, boxId, boxLastId)

                for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                    # Don't do it for the first pair, it was done earlier in the function
                    if idxPair == 0:
                        continue

                    pair = [chan, freq]
                    # Copy list of chained boxes (except the first (SPLIT) and
                    # the 2 last ones (feature aggreg, classifier trainer) and chain them.
                    listofBoxesToChain, nbOfOutputs = copyBoxList(root, boxList, locOffset, pair, 1, 2)
                    locOffset += locOffset

                    # Add an input to Feature Aggregator box in the current chain
                    addInputToBox(root, listofBoxesToChain[-1])
                    featAggInputIdx = countBoxInputs(root, listofBoxesToChain[-1]) - 1
                    linkBoxes(root, listofBoxesToChain, nbOfOutputs, featAggInputIdx)

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainScenUsingSplitAndClassifiers(splitStr, classifStr, chanFreqPairs, epochCount, scenXml):
    print("---Modifying " + scenXml + " with Selected Features")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # FIRST STEP : GET THE "SPLIT" IDENTITY BOXES
    splitBoxes = []
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == splitStr:
                splitBoxes.append(box)
                print("-- SPLIT POWSPECT " + str(len(splitBoxes)+1))
                continue

    # Find Id of Classifier trainer box
    boxLast = findBox(root, classifStr)
    boxLastId = boxLast.find("Identifier").text

    # FIRST STEP : modify existing branches in the scenario, using the first pair of features
    for splitbox in splitBoxes:
        boxId = splitbox.find("Identifier").text
        # Find all boxes chained btw this box and the last one (classifier trainer or processor)
        if boxId is not None and boxLastId is not None:
            boxList = findChainedBoxes(root, boxId, boxLastId)

        # Change parameters of particular boxes in this list of chained boxes
        for boxid in boxList:
            box = findBoxId(root, boxid)
            if box.find('Name').text == 'Channel Selector':
                print("-- CHANNEL SELECTOR BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][0]
                            print("            with " + xmlVal.text)
                            break

            if box.find('Name').text == 'Frequency Band Selector':
                print("-- FREQ SELECTION BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                        # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                        if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][1]
                            print("            with " + xmlVal.text)
                            break
            if box.find('Name').text == 'Epoch average':
                print("-- EPOCH AVERAGE BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Epoch count":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = str(epochCount)
                            print("            with " + xmlVal.text)
                            break

    if len(chanFreqPairs) > 1:
        # COPY/PASTE PROCESSING BRANCHES
        for splitbox in splitBoxes:
            locOffset = 120
            boxId = splitbox.find("Identifier").text
            # Find all boxes chained btw this split and the last (classifier trainer or processor)
            if boxId is not None and boxLastId is not None:
                boxList = findChainedBoxes(root, boxId, boxLastId)

                for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                    # Don't do it for the first pair, it was done earlier in the function
                    if idxPair == 0:
                        continue

                    pair = [chan, freq]
                    # Copy list of chained boxes (except the first (SPLIT) and
                    # the 2 last ones (feature aggreg, classifier trainer or processor) and chain them.
                    listofBoxesToChain, nbOfOutputs = copyBoxList(root, boxList, locOffset, pair, 1, 2)

                    # Add an input to Feature Aggregator box in the current chain
                    addInputToBox(root, listofBoxesToChain[-1])
                    featAggInputIdx = countBoxInputs(root, listofBoxesToChain[-1]) - 1
                    linkBoxes(root, listofBoxesToChain, nbOfOutputs, featAggInputIdx)

                    locOffset += locOffset

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainScenUsingSplitAndCsvWriter(splitStr, chanFreqPairs, epochCount, scenXml, trainingpath):
    print("---Modifying " + scenXml + " with Selected Features")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # FIRST STEP : GET THE "SPLIT" IDENTITY BOXES
    splitBoxes = []
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == splitStr:
                splitBoxes.append(box)
                print("-- SPLIT " + str(len(splitBoxes)+1))
                continue

    # Find Ids of CSV Writer boxes
    csvBoxes = []
    csvBoxesIds = []
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == "CSV Class1 Feat1":
                csvBoxes.append(box)
                csvBoxesIds.append(csvBoxes[-1].find("Identifier").text)
                print("-- CSV WRITER " + str(len(csvBoxes) + 1))
                continue
            elif box.find('Name').text == "CSV Class2 Feat1":
                csvBoxes.append(box)
                csvBoxesIds.append(csvBoxes[-1].find("Identifier").text)
                print("-- CSV WRITER " + str(len(csvBoxes) + 1))
                continue

    # FIRST STEP : modify existing branches in the scenario, using the first pair of features
    for splitbox in splitBoxes:
        boxId = splitbox.find("Identifier").text

        boxListFound = False
        # Find all boxes chained btw this box and the last one (csv Writer)
        for csvBoxId in csvBoxesIds:
            if boxId is not None and csvBoxId is not None:
                boxList = findChainedBoxes(root, boxId, csvBoxId)

                if boxList:
                    boxListFound = True
                    # Change parameters of particular boxes in this list of chained boxes
                    for boxid in boxList:
                        box = findBoxId(root, boxid)
                        if box.find('Name').text == 'Channel Selector':
                            print("-- CHANNEL SELECTOR BOX ")
                            for settings in box.findall('Settings'):
                                for setting in settings.findall('Setting'):
                                    if setting.find('Name').text == "Channel List":
                                        xmlVal = setting.find('Value')
                                        print("       replacing " + xmlVal.text)
                                        xmlVal.text = chanFreqPairs[0][0]
                                        print("            with " + xmlVal.text)
                                        break

                        if box.find('Name').text == 'Frequency Band Selector':
                            print("-- FREQ SELECTION BOX ")
                            for settings in box.findall('Settings'):
                                for setting in settings.findall('Setting'):
                                    # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                                    # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                                    if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                                        xmlVal = setting.find('Value')
                                        print("       replacing " + xmlVal.text)
                                        xmlVal.text = chanFreqPairs[0][1]
                                        print("            with " + xmlVal.text)
                                        break
                        if box.find('Name').text == 'Epoch average':
                            print("-- EPOCH AVERAGE BOX ")
                            for settings in box.findall('Settings'):
                                for setting in settings.findall('Setting'):
                                    if setting.find('Name').text == "Epoch count":
                                        xmlVal = setting.find('Value')
                                        print("       replacing " + xmlVal.text)
                                        xmlVal.text = str(epochCount)
                                        print("            with " + xmlVal.text)
                                        break
        if not boxListFound:
            print("-- ERROR IN TEMPLATE SCENARIO !! --")
            return

    if len(chanFreqPairs) > 1:
        # COPY/PASTE PROCESSING BRANCHES
        for splitbox in splitBoxes:

            locOffset = 120
            boxId = splitbox.find("Identifier").text
            boxListFound = False

            # Find all boxes chained btw this box and the last one (csv Writer)
            for csvBoxId in csvBoxesIds:
                if boxId is not None and csvBoxId is not None:
                    boxList = findChainedBoxes(root, boxId, csvBoxId)

                    if boxList:
                        boxListFound = True

                        for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                            # Don't do it for the first pair, it was done earlier in the function
                            if idxPair == 0:
                                continue

                            pair = [chan, freq]
                            # Copy list of chained boxes (except the first (SPLIT)) and chain them.
                            listofBoxesToChain, nbOfOutputs = copyBoxListGeneric(root, boxList, locOffset, pair, 1, 0)
                            csvWriter = findBoxId(root, listofBoxesToChain[-1])
                            oldName = csvWriter.find('Name').text.split("Feat")
                            changeBoxName(csvWriter, str(oldName[0] + 'Feat' + str(int(oldName[1])+ idxPair) ) )
                            linkBoxesGeneric(root, listofBoxesToChain, nbOfOutputs)

                            locOffset += locOffset

            if not boxListFound:
                print("-- ERROR IN TEMPLATE SCENARIO !! --")
                return

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainPartitions(trainParts, scenXml):
    print("---Modifying " + scenXml + " with train partitions: " + str(trainParts))
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # FIRST STEP AND
    # SIMPLEST CASE : just modify existing branches in the scenario.
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == 'Classifier trainer':
                print("-- CLASSIFIER TRAINER BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Number of partitions for k-fold cross-validation test":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = str(trainParts)
                            print("            with " + xmlVal.text)
                            break

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainIO(newFilename, newWeightsName, scenXml):
    print("---Modifying " + scenXml + " input")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PARSE SCENARIO GENERAL SETTINGS, AND MODIFY THEM ACCORDING TO THE PROVIDED
    # PARAMETER LIST
    for settings in root.findall('Settings'):
        for setting in settings.findall('Setting'):
            if setting.find('Name').text == "EEGData":
                xmlVal = setting.find('Value')
                xmlVal.text = newFilename
            elif setting.find('Name').text == "OutputWeights":
                xmlVal = setting.find('Value')
                xmlVal.text = newWeightsName

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyOnlineScenario(chanFreqPairs, scenXml):
    print("---Modifying " + scenXml + " with Selected Features")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # Assuming Power Spectrum pipeline...
    # There are two distinct scenario branches to modify here :
    # - Direct feedback branch : take the *first* electrode/freq pair
    # - Online Classification : behave exactly as for the training part (clone branches)

    channelSelectorBox = None
    # FIRST STEP AND
    # SIMPLEST CASE : just modify existing branches in the scenario.
    # (this takes care of the "direct feedback branch" + the first feature pair
    # of the "online classification" branch")
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):

            if box.find('Name').text == 'Channel Selector':
                print("-- CHANNEL SELECTOR BOX ")
                # keep box in memory for later...
                channelSelectorBoxIdx = box.find('Identifier').text
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][0]
                            print("            with " + xmlVal.text)
                            break

            if box.find('Name').text == 'Frequency Band Selector':
                print("-- FREQ SELECTION BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                        # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                        if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = chanFreqPairs[0][1]
                            print("            with " + xmlVal.text)
                            break

    if len(chanFreqPairs) > 1:
        # TOUGHEST CASE : NEED TO COPY/PASTE MULTIPLE PROCESSING
        # BRANCHES WITH CHANNEL SELECTOR, TIME EPOCH, AR COEFFS,
        # FREQ BAND SELECTOR AND SPECTRUM AVERAGE

        # First box in the chain: "SPLIT" IDENTITY BOX
        splitBox = None
        splitBoxId = None
        for boxes in root.findall('Boxes'):
            for box in boxes.findall('Box'):
                if box.find('Name').text == 'SPLIT':
                    print("-- SPLIT BOX")
                    splitBox = box
                    splitBoxId = splitBox.find("Identifier").text
                    continue

        # Last box in the chain: Classifier processor
        boxLast = findBox(root, "Classifier processor")
        boxLastId = boxLast.find("Identifier").text

        featAggInputIdx = 0

        # Find all chained box btw those two
        if splitBoxId is not None and boxLastId is not None:
            locOffset = 120
            boxList = findChainedBoxes(root, splitBoxId, boxLastId)

            for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                # Don't do it for the first pair, it was done earlier in the function
                if idxPair == 0:
                    continue

                pair = [chan, freq]
                # Copy list of chained boxes (except first (identity)
                # and 2 last (feature aggreg, classifier trainer)) and chain them.
                listofBoxesToChain, nbOfOutputs = copyBoxList(root, boxList, locOffset, pair, 1, 2)
                locOffset += locOffset

                # Add an input to Feature Aggregator box in the current chain
                addInputToBox(root, listofBoxesToChain[-1])
                featAggInputIdx += 1
                linkBoxes(root, listofBoxesToChain, nbOfOutputs, featAggInputIdx)

    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyConnectivityMetric(metric, scenXml):
    print("---Modifying " + scenXml + " with connectivity Metric: " + str(metric))
    tree = ET.parse(scenXml)
    root = tree.getroot()

    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == 'Connectivity Measure : Burg' or box.find('Name').text == 'Connectivity Measure':
                print("-- CONNECTIVITY BOX ")
                for settings in box.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Metric":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            xmlVal.text = str(metric)
                            print("            with " + xmlVal.text)
                            break

    # WRITE NEW XML
    tree.write(scenXml)
    return


def modifyTrainingFirstStep(runBasename, nbFeats, analysisPath, trainingPath, scenXml):
    print("---Modifying " + scenXml + " outputs")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    for settings in root.findall('Settings'):
        for setting in settings.findall('Setting'):
            if setting.find('Name').text == "InputClass1":
                xmlVal = setting.find('Value')
                newinput1 = str(runBasename + "-CONNECT-REST.csv")
                xmlVal.text = newinput1
                continue
            elif setting.find('Name').text == "InputClass2":
                xmlVal = setting.find('Value')
                newinput2 = str(runBasename + "-CONNECT-MI.csv")
                xmlVal.text = newinput2
                continue


    for feat in range(nbFeats):

        for boxes in root.findall('Boxes'):
            for box in boxes.findall('Box'):
                if box.find('Name').text == str('CSV Class1 Feat'+str(feat+1)):
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            if setting.find('Name').text == "Filename":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                class1featX = os.path.join(trainingPath, str(runBasename + "-class1-feat" + str(feat + 1)) + ".csv")
                                class1featX = class1featX.replace("\\", "/")
                                xmlVal.text = str(class1featX)
                                print("            with " + xmlVal.text)
                                break
                elif box.find('Name').text == str('CSV Class2 Feat'+str(feat+1)):
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            if setting.find('Name').text == "Filename":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                class2featX = os.path.join(trainingPath, str(runBasename + "-class2-feat" + str(feat + 1)) + ".csv" )
                                class2featX = class2featX.replace("\\", "/")
                                xmlVal.text = str(class2featX)
                                print("            with " + xmlVal.text)
                                break
    # WRITE NEW XML
    tree.write(scenXml)
    return

def modifyTrainingSecondStep(compositeFiles, nbFeats, newWeightsName, scenXml):
    print("---Modifying " + scenXml + " outputs")
    tree = ET.parse(scenXml)
    root = tree.getroot()

    # PARSE SCENARIO GENERAL SETTINGS, AND MODIFY THEM ACCORDING TO THE PROVIDED
    # PARAMETER LIST
    for settings in root.findall('Settings'):
        for setting in settings.findall('Setting'):
            if setting.find('Name').text == "OutputWeights":
                xmlVal = setting.find('Value')
                xmlVal.text = newWeightsName

    featAgg = []
    featAgg.append(findBox(root, "FeatAgg1") )
    featAgg.append(findBox(root, "FeatAgg2") )
    csvBoxes = []
    csvBoxes.append(findBox(root, "CSV class1 feat1") )
    csvBoxes.append(findBox(root, "CSV class2 feat1") )

    for classIdx in [0, 1]:
        locOffset = 120

        for feat in range(nbFeats):
            # first feat : don't copy, just edit the filename
            if feat == 0:
                for settings in csvBoxes[classIdx].findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Filename":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            for file in compositeFiles:
                                if str("class" + str(classIdx + 1) + "-feat" + str(
                                        feat + 1) + "-TRAINCOMPOSITE.csv") in file:
                                    classXfeatX = file.replace("\\", "/")
                                    xmlVal.text = str(classXfeatX)
                                    print("            with " + xmlVal.text)
                                    break
                continue
            else:
                newCsvIn = copyBox(root, csvBoxes[classIdx], locOffset)
                locOffset += locOffset
                oldName = csvBoxes[classIdx].find("Name").text
                changeBoxName(newCsvIn, oldName.replace("feat1", str('feat' + str(feat+1))) )
                for settings in newCsvIn.findall('Settings'):
                    for setting in settings.findall('Setting'):
                        if setting.find('Name').text == "Filename":
                            xmlVal = setting.find('Value')
                            print("       replacing " + xmlVal.text)
                            for file in compositeFiles:
                                if str("class" + str(classIdx+1) + "-feat" + str(feat+1) + "-TRAINCOMPOSITE.csv") in file:
                                    classXfeatX = file.replace("\\", "/")
                                    xmlVal.text = str(classXfeatX)
                                    print("            with " + xmlVal.text)
                                    break

                addInputToBox(root, featAgg[classIdx].find('Identifier').text)
                linkTwoBoxesGeneric(root, newCsvIn.find("Identifier").text,
                                    featAgg[classIdx].find("Identifier").text, 0, feat)



    # WRITE NEW XML
    tree.write(scenXml)
    return

##################
# HELPER FUNCTIONS
##################

def findPreviousBox(root, boxIdx):
    for links in root.findall('Links'):
        for link in links.findall('Link'):
            targetBox = link.find("Target")
            if targetBox.find('BoxIdentifier').text == boxIdx:
                sourceBox = link.find("Source")
                previousBox = findBoxId(root, sourceBox.find('BoxIdentifier').text)
                return previousBox

    return None

def addInputToBox(root, featAggBoxIdx):
    box = findBoxId(root, featAggBoxIdx)
    inputs = box.find('Inputs')
    input = inputs.find('Input')
    newinput = copy.deepcopy(input)
    inputs.append(newinput)

def countBoxInputs(root, boxIdx):
    nbInputs = 0
    box = findBoxId(root, boxIdx)
    inputs = box.find('Inputs')
    return len(inputs.findall('Input'))

def linkBoxes(root, listofBoxesToChain, nbOfOutputs, featAggInputIdx):
    links = root.find("Links")
    for idx, boxId in enumerate(listofBoxesToChain):

        if boxId is not listofBoxesToChain[-1]:

            link = ET.SubElement(links, "Link")
            identifier = ET.SubElement(link, "Identifier")
            newId1 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
            newId2 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
            identifier.text = str("(0x" + str(newId1) + ", 0x" + str(newId2) + ")")

            source = ET.SubElement(link, "Source")
            sourceBoxId = ET.SubElement(source, "BoxIdentifier")
            sourceBoxId.text = str(boxId)
            sourceBoxOut = ET.SubElement(source, "BoxOutputIndex")
            # We take the last output id of the box... (works for AR coeffs, for now...)
            # WARNING : this is a baaad patch
            sourceBoxOut.text = str(nbOfOutputs[idx] - 1)
            target = ET.SubElement(link, "Target")
            targetBoxId = ET.SubElement(target, "BoxIdentifier")
            targetBoxId.text = str(listofBoxesToChain[idx+1])
            targetBoxIn = ET.SubElement(target, "BoxInputIndex")
            if idx < len(listofBoxesToChain) - 2:
                targetBoxIn.text = str(0)
            else:
                targetBoxIn.text = str(featAggInputIdx)

def linkBoxesGeneric(root, listofBoxesToChain, nbOfOutputs):
    links = root.find("Links")
    for idx, boxId in enumerate(listofBoxesToChain):

        if boxId is not listofBoxesToChain[-1]:

            link = ET.SubElement(links, "Link")
            identifier = ET.SubElement(link, "Identifier")
            newId1 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
            newId2 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
            identifier.text = str("(0x" + str(newId1) + ", 0x" + str(newId2) + ")")

            source = ET.SubElement(link, "Source")
            sourceBoxId = ET.SubElement(source, "BoxIdentifier")
            sourceBoxId.text = str(boxId)
            sourceBoxOut = ET.SubElement(source, "BoxOutputIndex")
            # We take the last output id of the box... (works for AR coeffs, for now...)
            # WARNING : this is a baaad patch
            sourceBoxOut.text = str(nbOfOutputs[idx] - 1)
            target = ET.SubElement(link, "Target")
            targetBoxId = ET.SubElement(target, "BoxIdentifier")
            targetBoxId.text = str(listofBoxesToChain[idx+1])
            targetBoxIn = ET.SubElement(target, "BoxInputIndex")
            targetBoxIn.text = str(0)

def linkTwoBoxesGeneric(root, boxId1, boxId2, outputidx, inputidx):
    links = root.find("Links")
    link = ET.SubElement(links, "Link")

    identifier = ET.SubElement(link, "Identifier")
    newId1 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
    newId2 = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
    identifier.text = str("(0x" + str(newId1) + ", 0x" + str(newId2) + ")")

    source = ET.SubElement(link, "Source")
    sourceBoxId = ET.SubElement(source, "BoxIdentifier")
    sourceBoxId.text = str(boxId1)
    sourceBoxOut = ET.SubElement(source, "BoxOutputIndex")
    sourceBoxOut.text = str(outputidx)

    target = ET.SubElement(link, "Target")
    targetBoxId = ET.SubElement(target, "BoxIdentifier")
    targetBoxId.text = str(boxId2)
    targetBoxIn = ET.SubElement(target, "BoxInputIndex")
    targetBoxIn.text = str(inputidx)

def generateRandomHexId(length):
    return binascii.b2a_hex(os.urandom(length))


# Find a box by its name. Use ONLY to find a specific box in the whole tree.
# Most of times it's better to do it manually in a loop to process the xml on the fly...
def findBox(root, name):
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Name').text == name:
                return box

    return None

# Find a box by its ID. Use ONLY to find a specific box in the whole tree.
# Most of times it's better to do it manually in a loop to process the xml on the fly...
def findBoxId(root, idx):
    for boxes in root.findall('Boxes'):
        for box in boxes.findall('Box'):
            if box.find('Identifier').text == idx:
                return box

    return None

def copyBox(root, box, locOffset):
    horLocId = "(0x207c9054, 0x3c841b63)"

    boxes = root.find('Boxes')
    newbox = copy.deepcopy(box)
    # Modify some box parameters
    for node in newbox:
        # Create random id
        if node.tag == "Identifier":
            oldText = node.text
            oldIds = oldText.split(",")
            newId = str(generateRandomHexId(4)).replace("b", "").replace("\'", '')
            node.text = str(oldIds[0] + ", 0x" + str(newId) + ")")
            print("OLD ID : " + oldText + " // NEW ID : " + node.text)

        # Change location on designer
        elif node.tag == "Attributes":
            for attrib in node:
                if attrib.find("Identifier").text == horLocId:
                    loc = attrib.find('Value')
                    locInt = int(loc.text)
                    newLocInt = locInt + locOffset
                    loc.text = str(newLocInt)
                    continue

    boxes.append(newbox)
    return newbox

def copyBoxList(root, boxIdList, locOffset, chanFreqPair, nbDiscardTop, nbDiscardBottom):

    boxes = root.find('Boxes')
    # newBoxIdList & nbOfOutputs will serve for chaining later on.
    # Hence we add the first box to both lists (Stim based epoching)
    nbOfOutputs = [1]
    newBoxIdList = [boxIdList[0]]

    # List to parse : discard boxes we don't want to copy
    boxIdListToParse = boxIdList.copy()
    for i in range(nbDiscardTop):
        boxIdListToParse.pop(0)
    for i in range(nbDiscardBottom):
        boxIdListToParse.pop()

    for boxId in boxIdListToParse:
        # Find actual box in root and copy it
        for box in boxes:
            if box.find('Identifier').text == boxId:
                newBox = copyBox(root, box, locOffset)
                newBoxId = newBox.find('Identifier').text
                newBoxIdList.append(newBoxId)
                outputs = box.find('Outputs')
                nbOfOutputs.append(0)
                for output in outputs:
                    nbOfOutputs[-1] += 1

                # EDIT CHANNEL SELECTOR AND FREQ SELECTOR PARAMETERS
                if newBox.find('Name').text == "Channel Selector":
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            if setting.find('Name').text == "Channel List":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                xmlVal.text = chanFreqPair[0]
                                print("            with " + xmlVal.text)
                                continue
                elif newBox.find('Name').text == "Frequency Band Selector":
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                            # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                            if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                xmlVal.text = chanFreqPair[1]
                                print("            with " + xmlVal.text)
                                continue

                break

    # Add last element of the list, for future linking/chaining
    if len(newBoxIdList) > 1:
        newBoxIdList.append(boxIdList[len(boxIdList)-2])
        nbOfOutputs.append(1)

    print(newBoxIdList)

    return newBoxIdList, nbOfOutputs


def copyBoxListGeneric(root, boxIdList, locOffset, chanFreqPair, nbDiscardTop, nbDiscardBottom):

    boxes = root.find('Boxes')
    # newBoxIdList & nbOfOutputs will serve for chaining later on.
    # Hence we add the first box to both lists (Stim based epoching)
    nbOfOutputs = [1]
    newBoxIdList = [boxIdList[0]]

    # List to parse : discard boxes we don't want to copy
    boxIdListToParse = boxIdList.copy()
    for i in range(nbDiscardTop):
        boxIdListToParse.pop(0)
    for i in range(nbDiscardBottom):
        boxIdListToParse.pop()

    for boxId in boxIdListToParse:
        # Find actual box in root and copy it
        for box in boxes:
            if box.find('Identifier').text == boxId:
                newBox = copyBox(root, box, locOffset)
                newBoxId = newBox.find('Identifier').text
                newBoxIdList.append(newBoxId)
                outputs = box.find('Outputs')
                nbOfOutputs.append(0)
                if outputs:
                    for output in outputs:
                        nbOfOutputs[-1] += 1

                # EDIT CHANNEL SELECTOR AND FREQ SELECTOR PARAMETERS
                if newBox.find('Name').text == "Channel Selector":
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            if setting.find('Name').text == "Channel List":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                xmlVal.text = chanFreqPair[0]
                                print("            with " + xmlVal.text)
                                continue
                elif newBox.find('Name').text == "Frequency Band Selector":
                    for settings in box.findall('Settings'):
                        for setting in settings.findall('Setting'):
                            # POWER SPECTRUM PIPELINE: actual "freq band selector" box
                            # CONNECTIVITY PIPELINE: channel selector rebranded as freq band selector
                            if setting.find('Name').text == "Frequencies to select" or setting.find('Name').text == "Channel List":
                                xmlVal = setting.find('Value')
                                print("       replacing " + xmlVal.text)
                                xmlVal.text = chanFreqPair[1]
                                print("            with " + xmlVal.text)
                                continue

                break

    # For future linking/chaining
    if len(newBoxIdList) > 1:
        nbOfOutputs.append(1)

    print(newBoxIdList)

    return newBoxIdList, nbOfOutputs


# Find (linear) chain of boxes. No branches please !
def findChainedBoxes(root, firstBoxId, lastBoxId):
    boxList = [firstBoxId]
    condition = True

    foundLast = False

    for links in root.findall('Links'):

        while condition:
            found = False

            for link in links.findall('Link'):
                sourceBox = link.find("Source")
                id = sourceBox.find('BoxIdentifier')
                if sourceBox.find('BoxIdentifier').text == boxList[-1]:
                    targetBox = link.find("Target")
                    boxList.append(targetBox.find('BoxIdentifier').text)
                    found = True
                    if boxList[-1] == lastBoxId:
                        foundLast = True
                    break

            if not found or foundLast:
                condition = False

    if not foundLast:
        boxList = []

    print(boxList)
    return boxList

def changeBoxName(box, newName):
    box.find('Name').text = newName
    return

