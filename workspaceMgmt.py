import sys
import os
import json

def writeJson(file, newDict):
    with open(file, "w") as outfile:
        json.dump(newDict, outfile, indent=4)

def initializeNewWorkspace(jsonFile):
    newDict = {"HappyFeatVersion": "0.0"}
    writeJson(jsonFile, newDict)
    return

def setKeyValue(jsonFile, key, value):
    # Element can be whatever: None, int, str, list, dict...
    currentDict = {}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)
    currentDict[key] = value
    writeJson(jsonFile, currentDict)

def loadExtractedFiles(jsonFile, extractIdx):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    if currentDict["ExtractedSignalFiles"][extractIdx]:
        return currentDict["ExtractedSignalFiles"][extractIdx]
    else:
        return []

def addExtractedFile(jsonFile, extractIdx, filename):
    currentDict = {}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)

    if extractIdx not in currentDict["ExtractedSignalFiles"]:
        currentDict["ExtractedSignalFiles"][extractIdx] = [filename]
    else:
        if not currentDict["ExtractedSignalFiles"][extractIdx]:
            currentDict["ExtractedSignalFiles"][extractIdx] = [filename]
        elif filename not in currentDict["ExtractedSignalFiles"][extractIdx]:
            currentDict["ExtractedSignalFiles"][extractIdx].append(filename)

    writeJson(jsonFile, currentDict)

