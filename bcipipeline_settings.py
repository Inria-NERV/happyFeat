# --- bcipipeline_settings.py
# Contains all settings / parameters / useful info
# that the other scripts can use

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
                         "sc2-extract-select.xml",
                         "sc2-train.xml",
                         "sc3-online.xml",
                         "mi-stimulations.lua"]

global scenarioSettings
# Format : pairs ("setting name" , default value)
# 1 : None
# 2 : Power Spectrum based classification
# 3 : Connectivity
scenarioSettings = [None,
                    [("setting1", 1), ("setting2", 2), ("setting3", 3)],
                    [("setting1", 1), ("setting2", 2), ("setting3", 3)]]


