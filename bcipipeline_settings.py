# --- bcipipeline_settings.py
# Contains all settings / parameters / useful info
# that the other scripts can use

# TODO : instead of indexed lists, create option keys (PowSpectrum, Connectivity...)
# TODO : and make options dictionaries addressed by these keys
#     ex :
#     optionsTemplatesDir = {"": None,
#                            "PowSpectrum": "spectralpower-templates",
#                            "Connectivity": "connectivity-templates"}

global optionKeys
optionKeys = ["",
              "PowSpectrumGraz",
              "Connectivity"]

global optionsComboText
optionsComboText = {optionKeys[0]: "",
                    optionKeys[1]: "Power Spectrum based classification, Graz protocol",
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
                         "sc3-online.xml"]

global scenarioSettings
scenarioSettings = {optionKeys[0]: None,
                    # POWER SPECTRUM
                    optionKeys[1]:
                        {"TrialNb": [20, "Number of Trials"],
                         # "Stim1": ["LEFT", "Stimulation 1"],
                         # "Stim2": ["RIGHT", "Stimulation 2"],
                         "Baseline": [10, "Baseline duration (s)"],
                         "TrialWait": [1.5, "Wait for instruction (s)"],
                         "TrialLength": [1.5, "Instruction duration (s)"],
                         "EndTrial": [3, "End of trial duration (s)"],
                         "StimulationEpoch": [3, "Feat Extraction: Stimulation epoching (s)"],
                         "StimulationDelay": [0, "Feat Extraction: Stimulation epoching delay (s)"],
                         "TimeWindowLength": [0.4, "Feat Extraction: Time Window (Burg) (s)"],
                         "TimeWindowShift": [0.028, "Feat Extraction: Time Window overlapping (Burg) (s)"],
                         "AutoRegressiveOrder": [19, "Feat Extraction: Burg estimation order"],
                         "PsdSize": [500, "PSD Size"]},
                    # CONNECTIVITY
                    optionKeys[2]:
                        {"TrialNb": [20, "Number of Trials"],
                         # "Stim1": ["LEFT", "Stimulation 1"],
                         # "Stim2": ["RIGHT", "Stimulation 2"],
                         "Baseline": [10, "Baseline duration (s)"],
                         "TrialWait": [1.5, "Wait for instruction (s)"],
                         "TrialLength": [1.5, "Instruction duration (s)"],
                         "EndTrial": [3, "End of trial duration (s)"],
                         "StimulationEpoch": [3, "Feat Extraction: Stimulation epoching (s)"],
                         "StimulationDelay": [0, "Feat Extraction: Stimulation epoching delay (s)"],
                         "ConnectivityMetric": ["MSC", "Connectivity: Metric (MSC or IMCOH)"],
                         "WindowMethod": ["Hann", "Connectivity: Welch Window method (Hann or Hamming)"],
                         "WelchLength": [4, "Connectivity: length of a Connectivity estimation (s)"],
                         "WelchOverlap": [50, "Connectivity: Connectivity estimation overlapping (%)"],
                         "WelchWinLength": [0.25, "Connectivity: length of a Welch window (s)"],
                         "WelchWinOverlap": [50, "Connectivity: Welch window overlapping (%)"],
                         "FftSize": [256, "Connectivity: FFT Size"]}}

