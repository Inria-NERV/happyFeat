import os
import subprocess
from shutil import copyfile
import csv

from modifyOpenvibeScen import *

def generateMetadata(ovFile, openvibeDesigner):
    # Make a copy of Openvibe scenario, for safe modification...
    scenName = "toolbox-generate-metadata.xml"
    toolboxPath = "toolbox-scenarios"
    srcFile = os.path.join(os.getcwd(), toolboxPath, scenName)
    destFile = os.path.join(os.getcwd(), toolboxPath, scenName.replace(".xml", "-TEMP.xml"))
    print("---Copying file " + srcFile + " to " + destFile)
    copyfile(srcFile, destFile)

    inputParam = ovFile.replace("\\", "/")
    outputParam = inputParam.replace(".ov", "-META.csv")
    paramDict = {"EEGData": inputParam, "EEGMetaData": outputParam}

    # Modify scenario I/O
    modifyScenarioGeneralSettings(destFile, paramDict)

    # launch Openvibe toolbox scenario
    p = subprocess.Popen([openvibeDesigner, "--no-gui", "--play-fast", destFile],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        output = p.stdout.readline()
        if p.poll() is not None:
            break
        if output:
            print(str(output))
            if "Application terminated" in str(output):
                break

    return

def extractMetadata(metaCsv):
    rawHeader = None
    with open(metaCsv, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            print(row)
            rawHeader = row

    if not rawHeader:
        return None

    sampFreq = int(rawHeader[0].split(':')[1].removesuffix('Hz'))
    electrodeList = rawHeader[2:-3]

    return sampFreq, electrodeList


if __name__ == '__main__':

    openvibeDesigner = "C:\\openvibeTestArthur\\dist\\x64\\Release\\openvibe-designer.cmd"

    testSig = "C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\motor-imagery.ov"
    # generateMetadata(testSig, openvibeDesigner)

    testCsv = "C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\motor-imagery-META.csv"
    sampFreq, electrodeList = extractMetadata(testCsv)
    print("Sampling Freq: " + str(sampFreq))
    print("Electrodes (" + str(len(electrodeList)) + "): " + str(electrodeList))
