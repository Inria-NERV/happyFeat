import sys
import os
import json

def writeJson(file, newdict):
    with open(file, "w") as outfile:
        json.dump(newdict, outfile, indent=4)

def initializeNewWorkspace(jsonFile):
    newDict = {"HappyFeatVersion": "0.0"}
    writeJson(jsonFile, newDict)
    return

def saveSpecificField(jsonFile, newdict, field):
    currentDict = {}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)
    currentDict[field] = newdict[field]
    writeJson(jsonFile, currentDict)

def addDictInField(jsonFile, newDict, field):
    currentDict = {}
    with open(jsonFile, "r+") as myjson:
        currentDict = json.load(myjson)
    currentDict[field] = newDict
    writeJson(jsonFile, currentDict)

