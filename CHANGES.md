# Release notes
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## 0.3.0
- [feature] [Timeflux](https://timeflux.io/) can be used as an alternative BCI software to use. For now a single pipeline is available (2-class MI, with PSD using Welch's method)
- [tutorial] Tutorial & [associated documentation](https://happyfeat.readthedocs.io/en/latest/user_guide/tutorial/), using Timeflux
- [dependencies] Python 3.12.8, PySide6, updated some packages
- [install] Environment setup & package installation can be done using conda
- [workspace] Autofeat parameters now saved in the workspace file
- [feature] Most viz use [plotly](https://plotly.com/), rendering in a browser with added functionalities and interactivity
- [feature] Autofeat parameters can be set in a menu in the main GUI, and are now saved in the workspace
- [feature] Figures generated in HappyFeat are now saved in the workspace (html and png formats) 
- [feature] Added a mechanism to display the "signed" R2 map
- [doc] Updated with additional figures 
- [bugfix] Lots of minor fixes


## 0.2.2
- [pkg] package upload fixup for PyPi

## 0.2.1
- [feature] AutoFeat: added option to only consider R2 cases satisfying [class2-class1 > 0] (available via a checkbox in the "visualization" part of the GUI)
- [bugfix] reviewed/fixed how frequencies are propagated in the app (bugs appeared when using fres != 0): topomap, training, autofeat
- [bugfix] GUI fixes (greyed out areas, feature options in the "Train" part)
- [bugfix] SC3 scenario templates fixes
- [bugfix] Fixed potential crashes

## 0.2.0
- [feature] AutoFeat: Automatic training feature selection mechanism, with option to define a subselection of channels and frequencies for this selection.
- [feature] "Combination training" mechanism.
- [feature] Online BCI scenario generation, from a training attempt. Generates a readily usable OpenViBE scenario with selected features & classifier trained.
- [feature][experimental] Added "Advanced Mode" in the main GUI, enabling replaying signal files with a trained classifier (only for PSD and Connectivity pipelines)
- [feature] ERD/ERS available for Connectivity pipeline
- [dependencies] Changed from PyQt5 to PySide2
- [dependencies] Imposed some versions (MNE, matplotlib) due to modified behaviors (or removed/refactored functionailites), to be corrected in later versions of HF.
- [pipeline][experimental] One-class MI classification pipeline
- [feature][bugfix] Mechanism for handling invalid (NaN) values after extraction. Trials containing NaN values are automatically discarded at the visualization step. Extracted files are still usable in the visualisation part (hence no more "empty display"), but with a warning for the user.
- [test] Basic tests (& github action automation), more to come!
- [bugfix] Work thread management (template training scenarios, loading viz files when using multiple metrics)
- Various other [bugfix]'s...

## 0.1.3
- [bugfix] Forced MNE==0.23.2, newer versions cause problems when using topomap
- [bugfix] Experimental parameters fetching in workspace file

## 0.1.2
- packaging fixup: extractMetaData script: fixed error in resource management
- packaging fixup: removed config.json from pkg

## 0.1.0
- Initial version of HappyFeat