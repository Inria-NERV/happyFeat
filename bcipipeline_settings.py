# --- bcipipeline_settings.py
# Contains all settings / parameters / useful info
# that the other scripts can use

global optionKeys
optionKeys = ["",
              "PowSpectrumGraz",
              "Connectivity"]

global optionsComboText
optionsComboText = {optionKeys[0]: "",
                    optionKeys[1]: "Power Spectrum based classification, Graz protocol (2 classes)",
                    optionKeys[2]: "Functional Connectivity"}

global optionsNbParams
optionsNbParams = {optionKeys[0]: 0,
                   optionKeys[1]: 1,
                   optionKeys[2]: 2}

global optionsTemplatesDir
optionsTemplatesDir = {optionKeys[0]: None,
                       optionKeys[1]: "spectralpower-templates",
                       optionKeys[2]: "connectivity-templates"}

global templateScenFilenames
templateScenFilenames = ["sc1-monitor-acq.xml",
                         "sc2-extract-select.xml",
                         "sc2-train.xml",
                         "sc3-online.xml",
                         "mi-stimulations.lua"]

global scenarioSettings
scenarioSettings = {optionKeys[0]: None,

                    # POWER SPECTRUM
                    optionKeys[1]:
                        {"TrialNb": [20, "Number of Trials"],
                         "Class1": ["LEFT", "Class / Stimulation 1"],
                         "Class2": ["RIGHT", "Class / Stimulation 2"],
                         "Baseline": [10, "Duration before first trial (s)"],
                         "TrialWait": [1.5, "\"Get set\" duration (s)"],
                         "TrialLength": [1.5, "Trial duration (s)"],
                         "EndTrial": [3, "Inter-trial duration (s)"],

                         "StimulationEpoch": [3, "Epoch of Interest (EOI) (s)"],
                         "StimulationDelay": [0, "EOI offset (s)"],
                         "TimeWindowLength": [0.4, "Sliding Window (Burg) (s)"],
                         "TimeWindowShift": [0.028, "Overlap (Burg) (s)"],
                         "AutoRegressiveOrder": [19, "AR Burg estimation order"],
                         "PsdSize": [500, "FFT Size"]},

                    # CONNECTIVITY
                    optionKeys[2]:
                        {"TrialNb": [20, "Number of Trials"],
                         "Class1": ["LEFT", "Class / Stimulation 1"],
                         "Class2": ["RIGHT", "Class / Stimulation 2"],
                         "Baseline": [10, "Duration before first trial (s)"],
                         "TrialWait": [1.5, "\"Get set\" duration (s)"],
                         "TrialLength": [1.5, "Trial duration (s)"],
                         "EndTrial": [3, "Inter-trial duration (s)"],

                         "StimulationEpoch": [3, "Epoch of Interest (EOI) (s)"],
                         "StimulationDelay": [0, "EOI offset (s)"],
                         "ConnectivityMetric": ["MSC", "Connectivity Metric (MSC or IMCOH)"],
                         "WelchLength": [4, "Length of a Connectivity estimation (s)"],
                         "WelchOverlap": [50, "Connectivity estimation overlapping (%)"],
                         "WindowMethod": ["Hann", "Welch sliding window (Hann or Hamming)"],
                         "WelchWinLength": [0.25, "Welch sliding window length (s)"],
                         "WelchWinOverlap": [50, "Welch sliding window overlap (%)"],
                         "FftSize": [256, "Connectivity: FFT Size"]}}

global scenarioSettingsPartsLength
scenarioSettingsPartsLength = {optionKeys[0]: [0, 0],
                               optionKeys[1]: [7, 6],
                               optionKeys[2]: [7, 9]}
