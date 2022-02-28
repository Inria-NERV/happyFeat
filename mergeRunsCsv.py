import os
import numpy as np
import pandas as pd
import csv
import time

stimulationCodes = {
    "OVTK_GDF_Left": "769",
    "OVTK_GDF_Right": "770",
    "OVTK_StimulationId_Train": "33281",
}

def mergeRunsCsv(testSigList, class1, class2, class1Stim, class2Stim, tmin, tmax):
    start = time.time()

    # Load raw data and check sampling freqs
    rawData = []
    channels = []
    fsamp = None
    for sig in testSigList:
        data = pd.read_csv(sig)
        datanp = data.to_numpy()
        rawData.append(datanp)
        col = data.columns
        newfsamp = int(col[0].split(":")[1].removesuffix("Hz"))
        if fsamp is None:
            fsamp = newfsamp
        elif newfsamp != fsamp:
            return -1
        if len(channels) == 0:
            channels = col[2:-3]  # discard first 2 cols (time & epoch), and 3 last (event info)
        elif any(col[2:-3] != channels):
            return None

    outCsv = testSigList[0].replace("TRIALS", "TRAINCOMPOSITE")

    writeCompositeCsv(outCsv, rawData, class1Stim, class2Stim, channels, tmin, tmax, fsamp)

    end = time.time()
    print("==== ELAPSED: " + str(end - start))

    return outCsv


def writeCompositeCsv(filename, rawData, class1Stim, class2Stim, channels, tmin, tmax, fsamp):
    class1StimCode = stimulationCodes[class1Stim]
    class2StimCode = stimulationCodes[class2Stim]
    trainStimCode = stimulationCodes["OVTK_StimulationId_Train"]

    with open(filename, 'w', newline='') as csvfile:
        # write header
        fieldnames = [str('Time:' + str(int(fsamp)) + 'Hz'), 'Epoch']

        for elec in channels:
            fieldnames.append(elec)
        fieldnames.append("Event Id")
        fieldnames.append("Event Date")
        fieldnames.append("Event Duration")
        headwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
        headwriter.writeheader()

        writer = csv.writer(csvfile, delimiter=',')

        timeOffset = 0

        epochOffset = 0
        lastEpoch = 0
        newEpoch = True
        currentEpoch = -1

        timeIncrement = 1/fsamp

        for fileId, rawData in enumerate(rawData):
            nbElec = np.shape(rawData)[1] - 5
            # Process the data and reconstruct CSV file
            currentTime = 0

            for row in rawData:
                # copy row data, then we'll modify stuff
                dataToWrite = ["" for x in range(np.shape(row)[0])]
                if currentEpoch != int(row[1]):
                    currentEpoch = int(row[1])
                    timeOffset = round(timeOffset + 0.5, 8) # arbitrary, to create a gap between trials
                    newEpoch = True

                # Time field
                dataToWrite[0] = str(currentTime + timeOffset)
                # not directly currentTime += timeIncrement, because of Python's rounding error with floats
                # we might write 0.100000000000000002 which adds up...
                currentTime = round(currentTime + timeIncrement, 8)

                # Epoch field
                dataToWrite[1] = str(currentEpoch + epochOffset)
                lastEpoch = currentEpoch + epochOffset

                # Actual Data
                for elec in range(nbElec):
                    dataToWrite[elec+2] = str(row[elec+2])

                # Events
                # Only keep stimulations class 1 & 2, at the start of each
                # "stimulation based epoching", for reconstruction in OpenViBE
                if newEpoch:
                    # get stimulation fields
                    eventList = row[-3].split(":")
                    currentEventStimCode = None
                    if class1StimCode in eventList:
                        currentEventStimCode = class1StimCode
                    elif class2StimCode in eventList:
                        currentEventStimCode = class2StimCode

                    if currentEventStimCode:
                        # Add current Stimulation...
                        # Event id
                        dataToWrite[-3] = currentEventStimCode
                        # Event date
                        dataToWrite[-2] = dataToWrite[0]
                        # Event duration
                        dataToWrite[-1] = str("0")
                    else:  # not possible??
                        dataToWrite[-3] = ""
                        dataToWrite[-2] = ""
                        dataToWrite[-1] = ""
                    newEpoch = False
                else:
                    dataToWrite[-3] = ""
                    dataToWrite[-2] = ""
                    dataToWrite[-1] = ""

                writer.writerow(dataToWrite)

            print("= Merging run: ", str(fileId))
            timeOffset += currentTime
            epochOffset = lastEpoch+1

        # TODO : why do we need that ?
        # -- TEST : Add another (empty) frame with class2 stimulation
        # For *some reason* in OpenViBE the classifier trainer doesn't
        # take into account the feature vectors of the last stim, when using
        # a composite signal...
        timeOffset = round(timeOffset + 0.5, 8)
        dataToWrite = [str(timeOffset), str(epochOffset)]
        for elec in range(nbElec):
            dataToWrite.append("0.0")
        dataToWrite.append(class2StimCode)
        dataToWrite.append(str(timeOffset))
        dataToWrite.append(str("0"))
        writer.writerow(dataToWrite)
        # add more data frames to fit in an Epoch...
        remSamples = int(tmax*fsamp) - 1
        currentTime = timeIncrement
        for x in list(range(1, remSamples + 1, 1)):
            dataToWrite = [str(currentTime + timeOffset), str(epochOffset)]
            for elec in range(nbElec):
                dataToWrite.append("0.0")
            dataToWrite.append("")
            dataToWrite.append("")
            dataToWrite.append("")
            writer.writerow(dataToWrite)
            currentTime = round(currentTime + timeIncrement, 8)

        epochOffset += 1
        timeOffset += currentTime
        # -- END OF CONFUSING PART

        # Add an empty data frame, bearing only a "Train" Stimulation
        timeOffset = round(timeOffset + 0.5, 8)
        dataToWrite = ["" for x in range(np.shape(row)[0])]
        dataToWrite[0] = str(timeOffset)
        dataToWrite[1] = str(epochOffset)
        for elec in range(nbElec):
            dataToWrite[elec + 2] = str("0.0")
        dataToWrite[-3] = trainStimCode
        dataToWrite[-2] = dataToWrite[0]
        dataToWrite[-1] = str("0")
        writer.writerow(dataToWrite)

        # add more data frames to fit in an Epoch...
        remSamples = int(tmax*fsamp) - 1
        currentTime = timeIncrement
        for x in list(range(1, remSamples + 1, 1)):
            dataToWrite = ["" for x in range(np.shape(row)[0])]
            dataToWrite[0] = str(currentTime + timeOffset)
            dataToWrite[1] = str(epochOffset)
            currentTime = round(currentTime + timeIncrement, 8)
            for elec in range(nbElec):
                dataToWrite[elec + 2] = str("0.0")
            dataToWrite[-3] = ""
            dataToWrite[-2] = ""
            dataToWrite[-1] = ""
            writer.writerow(dataToWrite)

    return


if __name__ == '__main__':
    # Populate list of signals to merge
    testSig = ["C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\training\\motor-imagery-TRIALS.csv"]
    # testSig.append("C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\training\\motor-imagery-TRIALS.csv")
    # testSig.append("C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\signals\\training\\motor-imagery-TRIALS.csv")

    testSigList = testSig

    class1 = "LEFT"
    class2 = "RIGHT"
    class1Stim = "OVTK_GDF_Left"
    class2Stim = "OVTK_GDF_Right"
    tmin = 0
    tmax = 1.5

    mergeRunsCsv(testSigList, class1, class2, class1Stim, class2Stim, tmin, tmax)
