# --- bcipipeline_settings.py
# Contains all settings / parameters / useful info
# that the other scripts can use

global optionKeys
optionKeys = ["",
              "PowSpectrumGraz",
              "Connectivity"]

global optionsComboText
optionsComboText = {optionKeys[0]: "",
                    optionKeys[1]: "GrazBCI - Power Spectrum Features (2 classes)",
                    optionKeys[2]: "GrazBCI - Connectivity Features"}

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
                         "sc2-extract.xml",
                         "sc2-train-composite.xml",
                         "sc3-online.xml",
                         "mi-stimulations.lua"]

# global scenarioSettings
# scenarioSettings = {optionKeys[0]: None,
#
#                     # POWER SPECTRUM
#                     optionKeys[1]:
#                         {"TrialNb": [20, "Nb Trials per class"],
#                          "Class1": ["LEFT", "Class / Stimulation 1"],
#                          "Class2": ["RIGHT", "Class / Stimulation 2"],
#                          "Baseline": [10, "\"Get Set\" time (s)"],
#                          "TrialWait": [1.5, "Pre-Stimulus time (s)"],
#                          "TrialLength": [1.5, "Trial duration (s)"],
#                          "EndTrialMin": [2.5, "Inter-trial interval min (s)"],
#                          "EndTrialMax": [3.5, "Inter-trial interval max (s)"],
#                          "FeedbackLength": [3, "Feedback time (s) (online scenario)"],
#
#                          "StimulationEpoch": [1.5, "Epoch of Interest (EOI) (s)"],
#                          "StimulationDelay": [0, "EOI offset (s)"],
#                          "TimeWindowLength": [0.4, "Sliding Window (Burg) (s)"],
#                          "TimeWindowShift": [0.028, "Overlap (Burg) (s)"],
#                          "AutoRegressiveOrder": [19, "AR Burg Order"],
#                          "PsdSize": [500, "FFT Size"]},
#
#                     # CONNECTIVITY
#                     optionKeys[2]:
#                         {"TrialNb": [20, "Nb Trials per class"],
#                          "Class1": ["LEFT", "Class / Stimulation 1"],
#                          "Class2": ["RIGHT", "Class / Stimulation 2"],
#                          "Baseline": [10, "\"Get Set\" time (s)"],
#                          "TrialWait": [1.5, "Pre-Stimulus time (s)"],
#                          "TrialLength": [1.5, "Trial duration (s)"],
#                          "EndTrialMin": [2.5, "Inter-trial interval min (s)"],
#                          "EndTrialMax": [3.5, "Inter-trial interval max (s)"],
#                          "FeedbackLength": [3, "Feedback time (s) (online scenario)"],
#
#                          "StimulationEpoch": [1.5, "Epoch of Interest (EOI) (s)"],
#                          "StimulationDelay": [0, "EOI offset (s)"],
#                          "ConnectivityMetric": ["MSC", "Connectivity Metric (MSC or IMCOH)"],
#                          "WelchLength": [4, "Length of a Connectivity estimation (s)"],
#                          "WelchOverlap": [50, "Connectivity estimation overlapping (%)"],
#                          "WindowMethod": ["Hann", "Welch sliding window (Hann or Hamming)"],
#                          "WelchWinLength": [0.25, "Welch sliding window length (s)"],
#                          "WelchWinOverlap": [50, "Welch sliding window overlap (%)"],
#                          "FftSize": [256, "Connectivity: FFT Size"]}}
#
# global scenarioSettingsPartsLength
# scenarioSettingsPartsLength = {optionKeys[0]: [0, 0],
#                                optionKeys[1]: [9, 6],
#                                optionKeys[2]: [9, 9]}

global pipelineAcqSettings
pipelineAcqSettings = {optionKeys[0]: None,

                       # POWER SPECTRUM
                       optionKeys[1]:
                           {"TrialNb": 20,
                            "Class1": "LEFT",
                            "Class2": "RIGHT",
                            "Baseline": 20,
                            "TrialWait": 3,
                            "TrialLength": 3,
                            "EndTrialMin": 2.5,
                            "EndTrialMax": 3.5,
                            "FeedbackLength": 3,
                            },

                       # CONNECTIVITY
                       optionKeys[2]:
                           {"TrialNb": 20,
                            "Class1": "LEFT",
                            "Class2": "RIGHT",
                            "Baseline": 20,
                            "TrialWait": 3,
                            "TrialLength": 3,
                            "EndTrialMin": 2.5,
                            "EndTrialMax": 3.5,
                            "FeedbackLength": 3,
                            }
                       }

global pipelineExtractSettings
pipelineExtractSettings = {optionKeys[0]: None,

                           # POWER SPECTRUM
                           optionKeys[1]:
                               {"StimulationEpoch": 3,
                                "StimulationDelay": 0,
                                "TimeWindowLength": 0.25,
                                "TimeWindowShift": 0.161,
                                "AutoRegressiveOrder": 19,
                                "PsdSize": 500,
                                },

                           # CONNECTIVITY
                           optionKeys[2]:
                               {"StimulationEpoch": 1.5,
                                "StimulationDelay": 0,
                                "ConnectivityMetric": "MSC",
                                "WelchLength": 4,
                                "WelchOverlap": 50,
                                "WindowMethod": "Hann",
                                "WelchWinLength": 0.25,
                                "WelchWinOverlap": 50,
                                "FftSize": 256,
                                }

                           }

global paramIdText
paramIdText = {"TrialNb": "Nb Trials per class",
               "Class1": "Class / Stimulation 1",
               "Class2": "Class / Stimulation 2",
               "Baseline": "\"Get Set\" time (s)",
               "TrialWait": "Pre-Stimulus time (s)",
               "TrialLength": "Trial duration (s)",
               "EndTrialMin": "Inter-trial interval min (s)",
               "EndTrialMax": "Inter-trial interval max (s)",
               "FeedbackLength": "Feedback time (s) (online scenario)",
               "StimulationEpoch": "Epoch of Interest (EOI) (s)",
               "StimulationDelay": "EOI offset (s)",
               "TimeWindowLength": "Sliding Window (Burg) (s)",
               "TimeWindowShift": "Overlap (Burg) (s)",
               "AutoRegressiveOrder": "AR Burg Order",
               "PsdSize": "FFT Size",
               "ConnectivityMetric": "Connectivity Metric (MSC or IMCOH)",
               "WelchLength": "Length of a Connectivity estimation (s)",
               "WelchOverlap": "Connectivity estimation overlapping (%)",
               "WindowMethod": "Welch sliding window (Hann or Hamming)",
               "WelchWinLength": "Welch sliding window length (s)",
               "WelchWinOverlap": "Welch sliding window overlap (%)",
               "ConnectFftSize": "Connectivity: FFT Size"
               }
