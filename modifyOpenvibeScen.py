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

def modifyExtractionIO(scenXml, newFilename, newOutputSpect1, newOutputSpect2, newOutputBaseline1, newOutputBaseline2, newOutputTrials):
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

def modifyTrainScenario(chanFreqPairs, epochAvg, epochCount, scenXml):
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
            if epochAvg:
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

        # Find Ids of Stimulation based epoching box and Classifier trainer box
        boxLast = findBox(root, "Classifier trainer")
        boxLastId = boxLast.find("Identifier").text
        for box in splitBoxes:
            boxId = box.find("Identifier").text
            featAggInputIdx = 0
            locOffset = 120

            # Find all chained box btw those two
            if boxId is not None and boxLastId is not None:
                boxList = findChainedBoxes(root, boxId, boxLastId)

                for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                    # Don't do it for the first pair, it was done earlier in the function
                    if idxPair == 0:
                        continue

                    pair = [chan, freq]
                    # Copy list of chained boxes (except first (stim based epoching)
                    # and 2 last (feature aggreg, classifier trainer) and chain them.
                    listofBoxesToChain, nbOfOutputs = copyBoxList(root, boxList, locOffset, pair)
                    locOffset += locOffset

                    # Add an input to Feature Aggregator box in the current chain
                    addInputToBox(root, listofBoxesToChain[-1])
                    featAggInputIdx += 1
                    linkBoxes(root, listofBoxesToChain, nbOfOutputs, featAggInputIdx)

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
        locOffset = 120

        # Find all chained box btw those two
        if splitBoxId is not None and boxLastId is not None:
            boxList = findChainedBoxes(root, splitBoxId, boxLastId)

            for idxPair, [chan, freq] in enumerate(chanFreqPairs):
                # Don't do it for the first pair, it was done earlier in the function
                if idxPair == 0:
                    continue

                pair = [chan, freq]
                # Copy list of chained boxes (except first (identity)
                # and 2 last (feature aggreg, classifier trainer)) and chain them.
                listofBoxesToChain, nbOfOutputs = copyBoxList(root, boxList, locOffset, pair)
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

def copyBoxList(root, boxIdList, locOffset, chanFreqPair):

    boxes = root.find('Boxes')
    # newBoxIdList & nbOfOutputs will serve for chaining later on.
    # Hence we add the first box to both lists (Stim based epoching)
    nbOfOutputs = [1]
    newBoxIdList = [boxIdList[0]]
    # List to parse : discard first and 2 last ones, we don't want them copied...
    boxIdListToParse = boxIdList.copy()
    boxIdListToParse.pop(0)
    boxIdListToParse.pop()
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


# Find (linear) chain of boxes. No branches please !
def findChainedBoxes(root, firstBoxId, lastBoxId):
    boxList = [firstBoxId]
    condition = True

    for links in root.findall('Links'):

        while condition:
            found = False
            foundLast = False
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

    print(boxList)
    return boxList

