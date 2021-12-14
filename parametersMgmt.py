import os
import sys
import json

class PipelineParams:
    pipelineType = []
    electrodeList = []

    fSampling = []
    trialLengthSec = []
    trialNb = []
    fftBins = []


    burgWindowLength = []
    burgWindowOverlap = []
    burgWindowShift = []
    burgFilterOrder = []
    burgPsdSize = []

    def __init__(self):
        self.pipelineType = "PowerSpectrum"
        self.electrodeList = ['Fp1','Fp2','F7','F3','Fz','F4','F8','FC5','FC1','FC2','FC6','T7','C3','Cz','C4','T8','TP9','CP5','CP1','CP2','CP6','TP10','P7','P3','Pz','P4','P8','PO9','O1','Oz','O2','PO10']

        self.fSampling = 500
        self.trialLengthSec = 3
        self.trialNb = 20
        self.fftBins = 251

        self.burgWindowLength = 0.4
        self.burgWindowOverlap = 0.028
        self.burgWindowShift = self.burgWindowLength - self.burgWindowOverlap
        self.burgFilterOrder = 19
        self.burgPsdSize = 500


def readJsonFile(filename):
    debug = False
    if debug:
        print("READING JSON FILE " + str(filename))

    f = open(filename)
    data = json.load(f)
    if debug:
        for i in data:
            print(i)

    f.close()
    return
