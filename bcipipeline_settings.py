# bcipipeline_settings.py
import os


global options
options = ["                       ",
           "Power Spectrum based classification, Graz protocol",
           "Functional Connectivity"]

global optionsNbParams
optionsNbParams = [0,
                   1,
                   2]

global optionsTemplatesDir
optionsTemplatesDir = [None,
                       "spectralpower-templates",
                       "connectivity-templates"]

global templateScenFilenames
templateScenFilenames = ["sc1-monitor-acq.xml",
                         "sc2-extract-select-train.xml",
                         "sc3-online.xml",
                         "mi-stimulations.lua"]