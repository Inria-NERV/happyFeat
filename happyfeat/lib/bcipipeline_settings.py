# --- bcipipeline_settings.py
# Contains all settings / parameters / useful info
# that the other scripts can use

global optionKeys
optionKeys = ["",
              "PowSpectrumGraz",
              "Connectivity",
              "Psd+Connect",
              "BCINET-AutoFeatures"]

global optionsComboText
optionsComboText = {optionKeys[0]: "",
                    optionKeys[1]: "GrazBCI - Power Spectrum Features (2 classes)",
                    optionKeys[2]: "GrazBCI - Connectivity Features (2 classes)",
                    optionKeys[3]: "GrazBCI - Pow.Spect. + Connectivity Features (2 classes)",
                    optionKeys[4]: "BCINET - Pow.Spect. + Connectivity (1 class, auto selection)"}

global optionsTemplatesDir
optionsTemplatesDir = {optionKeys[0]: None,
                       optionKeys[1]: "templates-spectralpower",
                       optionKeys[2]: "templates-connectivity",
                       optionKeys[3]: "templates-mixed",
                       optionKeys[4]: "templates-mixed-1-class"}

global templateScenFilenames
templateScenFilenames = ["sc1-monitor-acq.xml",
                         "sc2-extract.xml",
                         "sc2-train-composite.xml",
                         "sc3-online.xml",
                         "sc2-train-speedup-firststep.xml",
                         "sc2-train-speedup-finalize.xml",
                         "sc4-run-replay.xml",
                         "mi-stimulations.lua"]

global connectMetrics
connectMetrics = [#"MagnitudeSquaredCoherence",
                  #"ImaginaryCoherence",
                  "Coherence",
                  "AbsImaginaryCoherence"]

global connectMetricsComboText
connectMetricsComboText = { #connectMetrics[0]: "Magnitude Squared Coh.",
                            #connectMetrics[1]: "Imag(Coh.)",
                            connectMetrics[0]: "abs(Coh.)",
                            connectMetrics[1]: "abs(Imag(Coh.))"}

global pipelineAcqSettings
pipelineAcqSettings = { "TrialNb": 20,
                        "Class1": "MI",  # OV : LEFT
                        "Class2": "REST",  # OV : RIGHT
                        "Baseline": 20,
                        "TrialWait": 3,
                        "TrialDelay": 1,
                        "TrialLength": 3,
                        "EndTrialMin": 2.5,
                        "EndTrialMax": 3.5,
                        "FeedbackLength": 3,
                        }

global pipelineExtractSettings
pipelineExtractSettings = {optionKeys[0]: None,

                           # POWER SPECTRUM
                           optionKeys[1]:
                               {"StimulationEpoch": "3",
                                "StimulationDelay": "1",
                                "TimeWindowLength": "0.25",
                                "TimeWindowShift": "0.161",
                                # "AutoRegressiveOrder": "19",
                                "AutoRegressiveOrderTime": "0.038",
                                # "PsdSize": "500",
                                "FreqRes": "1",
                                },

                           # CONNECTIVITY
                           optionKeys[2]:
                               {"StimulationEpoch": "3",
                                "StimulationDelay": "1",
                                "ConnectivityMetric": connectMetrics[1],
                                "ConnectivityLength": "0.25",
                                "ConnectivityOverlap": "36",
                                # "AutoRegressiveOrder": "12",
                                "AutoRegressiveOrderTime": "0.038",
                                # "PsdSize": "256",
                                "FreqRes": "1",
                                },

                           # POWER SPECTRUM + CONNECTIVITY
                           optionKeys[3]:
                               {"StimulationEpoch": "3",
                                "StimulationDelay": "1",
                                "TimeWindowLength": "0.25",
                                "TimeWindowShift": "0.161",
                                "ConnectivityMetric": connectMetrics[1],
                                "ConnectivityLength": "0.25",
                                "ConnectivityOverlap": "36",
                                # "AutoRegressiveOrder": "12",
                                "AutoRegressiveOrderTime": "0.038",
                                # "PsdSize": "256",
                                "FreqRes": "1",
                                },

                           optionKeys[4]:
                               {"StimulationEpoch": "3",
                                "StimulationDelay": "1",
                                "TimeWindowLength": "0.25",
                                "TimeWindowShift": "0.161",
                                "ConnectivityMetric": connectMetrics[1],
                                "ConnectivityLength": "0.25",
                                "ConnectivityOverlap": "36",
                                # "AutoRegressiveOrder": "12",
                                "AutoRegressiveOrderTime": "0.038",
                                # "PsdSize": "256",
                                "FreqRes": "1",
                                }
                           }

global paramIdText
paramIdText = {"TrialNb": "Nb Trials per class",
               "Class1": "Class / Stimulation 1",
               "Class2": "Class / Stimulation 2",
               "Baseline": "\"Get Set\" time (s)",
               "TrialWait": "Pre-Stimulus time (s)",
               "TrialDelay": "Offset/Delay between stimulus and actual trial (s)",
               "TrialLength": "Trial duration (s)",
               "EndTrialMin": "Inter-trial interval min (s)",
               "EndTrialMax": "Inter-trial interval max (s)",
               "FeedbackLength": "Feedback time (s) (online scenario)",
               "StimulationEpoch": "Epoch of Interest (EOI) (s)",
               "StimulationDelay": "EOI offset (s)",
               "TimeWindowLength": "Sliding Window (PSD) (s)",
               "TimeWindowShift": "Window Shift (PSD) (s)",
               "AutoRegressiveOrder": "AR Burg Order (samples)",
               "AutoRegressiveOrderTime": "Auto-regressive estim. length (s)",
               "PsdSize": "FFT Size",
               "FreqRes": "Frequency resolution (ratio)",
               "ConnectivityMetric": "Connectivity Estimator",
               "ConnectivityLength": "Sliding Window (Connect.) (s)",
               "ConnectivityOverlap": "Window overlap (Connect.) (%)",
               "ConnectivityMethod": "Method used for connectivity (Burg or Welch)",
               "WelchLength": "Length of a Connectivity estimation (s)",
               "WelchOverlap": "Connectivity estimation overlapping (%)",
               "WindowMethod": "Welch sliding window (Hann or Hamming)",
               "WelchWinLength": "Welch sliding window length (s)",
               "WelchWinOverlap": "Welch sliding window overlap (%)",
               "ConnectFftSize": "Connectivity: FFT Size",
               "ChannelSubset": "Subset of sensors (sep. with \";\". Empty for all sensors)"
               }
