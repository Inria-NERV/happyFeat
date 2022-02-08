import os
import sys
import shutils
import mne
import numpy as np
import csv
import time


stimulationCodes = {
    "OVTK_GDF_Start_Of_Trial": "768",
    "OVTK_GDF_Left": "769",
    "OVTK_GDF_Right": "770",
    "OVTK_GDF_Feedback_Continuous": "781",
    "OVTK_GDF_Cross_On_Screen": "786",
    "OVTK_GDF_End_Of_Trial": "800",
    "OVTK_GDF_Incorrect": "898",
    "OVTK_GDF_End_Of_Session": "1010",
    "OVTK_StimulationId_ExperimentStart": "32769",
    "OVTK_StimulationId_ExperimentStop": "32770",
    "OVTK_StimulationId_BaselineStart": "32775",
    "OVTK_StimulationId_BaselineStop": "32776",
    # "OVTK_StimulationId_VisualStimulationStart": "32779",
    "OVTK_StimulationId_VisualStimulationStar": "32779",
    "OVTK_StimulationId_Label_00": "33024",
    "OVTK_StimulationId_Label_01": "33025",
    "OVTK_StimulationId_Train": "33281",
    "OVTK_StimulationId_Beep": "33282",
    "OVTK_StimulationId_NonTarget": "33286",
}

electrodes = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "FC5", "FC1", "FC2", "FC6", "T7",
              "C3", "Cz", "C4", "T8", "TP9", "CP5", "CP1", "CP2", "CP6", "TP10", "P7", "P3", "Pz", "P4",
              "P8", "PO9", "O1", "Oz", "O2", "PO10"]


def mergeRuns(testSigList, class1, class2, class1Stim, class2Stim, tmin, tmax):
    # start = time.time()

    class1Files= []
    class2Files = []
    for run in testSigList:
        class1Files.append(str(run + "-" + class1 + ".edf"))
        class2Files.append(str(run + "-" + class2 + ".edf"))

    # Load raw data and check sampling freqs
    rawClass1 = []
    rawClass2 = []
    fsamp = None
    for sig in class1Files:
        rawClass1.append(mne.io.read_raw_edf(sig, preload=True))
        info = rawClass1[-1].info
        print(info)
        if fsamp is None:
            fsamp = info["sfreq"]
        elif info["sfreq"] != fsamp:
            return -1
    for sig in class2Files:
        rawClass2.append(mne.io.read_raw_edf(sig, preload=True))
        info = rawClass2[-1].info
        print(info)
        if info["sfreq"] != fsamp:
            return -1

    outCsv = str(testSigList[0] + "-TRAINCOMPOSITE-" + class1 + "-" + class2 + ".csv")
    
    writeCompositeCsv(outCsv, rawClass1, rawClass2, class1Stim, class2Stim, tmin, tmax, fsamp)

    # end = time.time()
    # print("==== ELAPSED: " + str(end - start))

    return outCsv


def writeCompositeCsv(filename, mneRawDataList1, mneRawDataList2, class1Stim, class2Stim, tmin, tmax, fsamp):
    class1StimCode = stimulationCodes[class1Stim]
    class2StimCode = stimulationCodes[class2Stim]
    trainStimCode = stimulationCodes["OVTK_StimulationId_Train"]

    nbOfRuns = len(mneRawDataList1)

    with open(filename, 'w', newline='') as csvfile:
        # write header
        # TODO change sampling freq
        fieldnames = [str('Time:' + str(int(fsamp)) + 'Hz'), 'Epoch']
        for elec in electrodes:
            fieldnames.append(elec)
        fieldnames.append("Event Id")
        fieldnames.append("Event Date")
        fieldnames.append("Event Duration")
        headwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
        headwriter.writeheader()

        writer = csv.writer(csvfile, delimiter=',')

        timeOffset = 0
        epoch = -1
        epochSample = 0
        epochLength = 32
        globalSampleCount = 0
        samplesPerStimulationEpoch = tmax*fsamp

        for fileId, mneRawData in enumerate(mneRawDataList1+mneRawDataList2):
            currentClassStimCode = class1StimCode
            if fileId >= len(mneRawDataList1):
                currentClassStimCode = class2StimCode

            # load data, times
            rawData = mneRawData.get_data()
            times = mneRawData.times
            
            # Process the data and reconstruct CSV file
            currentSignalSample = 0
            nbElec = np.shape(rawData)[0]
            for timeid, time in enumerate(times):
                # Time field
                dataToWrite = [str(time + timeOffset)]

                # Epoch field
                if globalSampleCount % epochLength == 0:
                    epoch += 1
                dataToWrite.append(str(epoch))

                # Actual data
                for elec in range(nbElec):
                    temp = str(rawData[elec][currentSignalSample])
                    dataToWrite.append(temp)

                # Events
                # Only add "Stimulation_Class1" & Class2 at the start of each 
                # "stimulation based epoching", for reconstruction in OpenViBE
                # eventlist management
                if currentSignalSample % samplesPerStimulationEpoch == 0:
                    # Add current Stimulation...
                    # Event id
                    dataToWrite.append(currentClassStimCode)
                    # Event date
                    dataToWrite.append(str(time + timeOffset))
                    # Event duration
                    dataToWrite.append(str("0"))
                # else if fileId == len(mneRawDataList1+mneRawDataList2)-1 and timeId == len(times)-1:

                else:
                    dataToWrite.append("")
                    dataToWrite.append("")
                    dataToWrite.append("")

                writer.writerow(dataToWrite)
                currentSignalSample += 1
                globalSampleCount += 1

            timeOffset += times[-1] + times[1]
            print("= Last Timestamp: ", str(timeOffset), " (", str(timeOffset / 60), "minutes)")

        # Add an empty data frame, bearing only a "Train" Stimulation
        dataToWrite = [str(timeOffset)]
        dataToWrite.append(str(epoch))
        for elec in range(nbElec):
            dataToWrite.append("0.0")
        dataToWrite.append(trainStimCode)
        dataToWrite.append(str(timeOffset))
        dataToWrite.append(str("0"))
        writer.writerow(dataToWrite)
        globalSampleCount += 1

        # add more data frames to fit in an Epoch...
        remSamples = epochLength - (globalSampleCount % epochLength)
        if remSamples != 0:
            for x in list(range(1, remSamples+1, 1)):
                dataToWrite = [str(timeOffset + x/fsamp)]
                dataToWrite.append(str(epoch))
                for elec in range(nbElec):
                    dataToWrite.append("0.0")
                dataToWrite.append("")
                dataToWrite.append("")
                dataToWrite.append("")
                writer.writerow(dataToWrite)

    return


if __name__ == '__main__':

    # Populate list of signals to merge
    testSig = ["C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\motor-imagery"]
    testSig.append("C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\motor-imagery2")
    testSig.append("C:\\Users\\arthur.desbois\\Documents\\dev\\openvibeScripting\\openvibe-automation\\generated\\motor-imagery3")

    testSigList = testSig

    class1 = "Left"
    class2 = "Right"
    class1Stim = "OVTK_GDF_Left"
    class2Stim = "OVTK_GDF_Right"
    tmin = 0
    tmax = 1.5

    mergeRuns(testSigList, class1, class2, class1Stim, class2Stim, tmin, tmax)
