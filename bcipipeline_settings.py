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
                    optionKeys[2]: "GrazBCI - Connectivity Features (2 classes)"}

global optionsNbParams
optionsNbParams = {optionKeys[0]: 0,
                   optionKeys[1]: 1,
                   optionKeys[2]: 2}

global optionsTemplatesDir
optionsTemplatesDir = {optionKeys[0]: None,
                       optionKeys[1]: "templates-spectralpower",
                       optionKeys[2]: "templates-connectivity"}

global templateScenFilenames
templateScenFilenames = ["sc1-monitor-acq.xml",
                         "sc2-extract.xml",
                         "sc2-train-composite.xml",
                         "sc3-online.xml",
                         "mi-stimulations.lua"]

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
                                # "AutoRegressiveOrder": 19,
                                "AutoRegressiveOrderTime": 0.038,
                                # "PsdSize": 500,
                                "FreqRes": 1,
                                },

                           # CONNECTIVITY
                           optionKeys[2]:
                               {"StimulationEpoch": 1.5,
                                "StimulationDelay": 0,
                                "ConnectivityMetric": "MSC",
                                "ConnectivityLength": 1,
                                "ConnectivityOverlap": 50,
                                # "ConnectivityMethod" : "Burg"
                                # "AutoRegressiveOrder": 12,
                                "AutoRegressiveOrderTime": 0.024,
                                # "WindowMethod": "Hann",
                                # "WelchWinLength": 0.25,
                                # "WelchWinOverlap": 50,
                                # "PsdSize": 256,
                                "FreqRes": 1,
                                # "ChannelSubset": "",
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
               "TimeWindowShift": "Window Shift (Burg) (s)",
               "AutoRegressiveOrder": "AR Burg Order (samples)",
               "AutoRegressiveOrderTime": "Auto-regressive estim. length (s)",
               "PsdSize": "FFT Size",
               "FreqRes": "Frequency resolution (ratio)",
               "ConnectivityMetric": "Connectivity Metric (MSC or IMCOH)",
               "ConnectivityLength": "Length of a connectivity measure (s)",
               "ConnectivityOverlap": "Overlap between connectivity measures (%)",
               "ConnectivityMethod": "Method used for connectivity (Burg or Welch)",
               "WelchLength": "Length of a Connectivity estimation (s)",
               "WelchOverlap": "Connectivity estimation overlapping (%)",
               "WindowMethod": "Welch sliding window (Hann or Hamming)",
               "WelchWinLength": "Welch sliding window length (s)",
               "WelchWinOverlap": "Welch sliding window overlap (%)",
               "ConnectFftSize": "Connectivity: FFT Size",
               "ChannelSubset": "Subset of sensors (sep. with \";\". Empty for all sensors)"
               }
