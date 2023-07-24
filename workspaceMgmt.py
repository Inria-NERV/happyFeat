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

def loadExtractedFiles(jsonFile, sessionId):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    if currentDict["Sessions"][sessionId]:
        return currentDict["Sessions"][sessionId]["ExtractedSignalFiles"]
    else:
        return []

def addExtractedFile(jsonFile, sessionId, filename):
    currentDict = {}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)
    currentDict["Sessions"][sessionId]["ExtractedSignalFiles"].append(filename)
    writeJson(jsonFile, currentDict)

def newSession(jsonFile, paramDict, newId, newParamDict):
    paramDict["Sessions"][newId] = {"ExtractionParams": newParamDict,
                                    "ExtractedSignalFiles": [],
                                    "TrainingAttempts": []}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)

    if "Sessions" in currentDict:
        sessionsDict = currentDict["Sessions"]
    else:
        currentDict["Sessions"] = {}
        sessionsDict = currentDict["Sessions"]

    sessionsDict[newId] = paramDict["Sessions"][newId]
    currentDict["Sessions"] = sessionsDict
    writeJson(jsonFile, currentDict)

