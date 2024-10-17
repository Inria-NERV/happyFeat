import sys
import os
import json

def writeJson(file, newDict):
    with open(file, "w") as outfile:
        json.dump(newDict, outfile, indent=4)

def initializeNewWorkspace(jsonFile):
    newDict = {"HappyFeatVersion": "0.2.2"}
    writeJson(jsonFile, newDict)
    return

def setKeyValue(jsonFile, key, value):
    # Element can be whatever: None, int, str, list, dict...
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    currentDict[key] = value
    writeJson(jsonFile, currentDict)

def getExperimentalParameters(jsonFile):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
        if currentDict["AcquisitionParams"]:
            return currentDict["AcquisitionParams"]
        else:
            return None

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
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    currentDict["Sessions"][sessionId]["ExtractedSignalFiles"].append(filename)
    writeJson(jsonFile, currentDict)

def checkIfTrainingAlreadyDone(jsonFile, sessionId, listFiles, listFeatures):
    # Checks if a training has already been attempted with such
    # parameters.
    # Returns:
    # - result (bool) : true/false
    # - idx (str) : if result is true, idx of attempt, if false, lastidx+1
    # - score (str) : if result is true, score of attempt, if false, None
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    if currentDict["Sessions"][sessionId]["TrainingAttempts"] == {}:
        return False, "1", None
    for idx in currentDict["Sessions"][sessionId]["TrainingAttempts"]:
        attempt = currentDict["Sessions"][sessionId]["TrainingAttempts"][idx]
        if set(listFiles) == set(attempt["SignalFiles"]):
            if set(listFeatures) == set(attempt["Features"]):
                if all([set(listFeatures[item]) == set(attempt["Features"][item]) for item in listFeatures]):
                    score = attempt["Score"]
                    return True, idx, score
    return False, str(int(idx)+1), None

def addTrainingAttempt(jsonFile, sessionId, listFiles, compositeFile, listFeatures, score):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    # get last training id...
    if not "1" in currentDict["Sessions"][sessionId]["TrainingAttempts"]:
        lastIdx = 1
    else:
        for idx in currentDict["Sessions"][sessionId]["TrainingAttempts"]:
            lastIdx = idx
        lastIdx = str(int(lastIdx)+1)

    newTrainAttempt = {"SignalFiles": listFiles, "CompositeFile": compositeFile, "Features": listFeatures, "Score": str(score)}
    currentDict["Sessions"][sessionId]["TrainingAttempts"][lastIdx] = newTrainAttempt
    writeJson(jsonFile, currentDict)

def replaceTrainingAttempt(jsonFile, sessionId, attemptId, listFiles, compositeFile, listFeatures, score):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)
    newTrainAttempt = {"SignalFiles": listFiles, "CompositeFile": compositeFile, "Features": listFeatures,
                       "Score": str(score)}
    currentDict["Sessions"][sessionId]["TrainingAttempts"][attemptId] = newTrainAttempt
    writeJson(jsonFile, currentDict)

def getTrainingResults(jsonFile, sessionId):
    currentDict = {}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)

    return currentDict["Sessions"][sessionId]["TrainingAttempts"]

def newSession(jsonFile, paramDict, newId, newParamDict):
    paramDict["Sessions"][newId] = {"ExtractionParams": newParamDict,
                                    "ExtractedSignalFiles": [],
                                    "TrainingAttempts": {}}
    with open(jsonFile, "r") as myjson:
        currentDict = json.load(myjson)

    if "Sessions" in currentDict:
        sessionsDict = currentDict["Sessions"]
    else:
        currentDict["Sessions"] = {}
        sessionsDict = currentDict["Sessions"]

    sessionsDict[newId] = paramDict["Sessions"][newId]
    currentDict["Sessions"] = sessionsDict
    writeJson(jsonFile, currentDict)

