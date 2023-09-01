# Documentation happyFeat

HappyFeat is a framework / software suite aiming to simplify the use of BCI pipelines in clinical settings.

It consists of Qt-based GUIs and a set of scripts, allowing to generate and use BCI pipelines, via OpenViBE standardized scenarios: acquisition & monitoring, feature extraction & selection, classifier training, online classification.

The focus is put on ease of use, trial-and-error training of the classifier, and fast and efficient analysis of features of interest from BCI sessions.

## Key Features

* Automatic generation of scenarios via a GUI. No need to open every scenario in the OpenViBE designer, to set every parameter and triple check everything.
* Easy to use GUI allowing to visualize classification features (R² map, Power Spectral Densities, Time/frequency analysis, Brain Topography), and select features of interest for training a classifier.
* Feature selection and classifier training can be done multiple times in a row, until satisfactory results are achieved. OpenViBE scenarios are updated automatically in the background. 
* Multiple runs (sessions of acquired EEG signals) can be processed at once, to visualize averaged spectral features, and to train the classifier with concatenated trials. 
* Automatically find the best combination of runs for training the classifier.

* Available pipelines : 
  * Power Spectrum (Burg method) based classification, Graz protocol (2 classes)
  * Functional Connectivity - based Node Strength
  * Mixing Both PSD and Connectivity
* Available classifiers:
  * LDA
  * *more coming soon!*

* *Coming soon : More Features!*
  * *More feature classes, more classification algos*
  * *Particle swarm algorithm for determining optimal AutoRegressive model order*

# Requirements

* Python 3.9 or more recent
* Python packages : shutils / PyQt5 / numpy / MNE / matplotlib / scipy / spectrum / statsmodel / pandas
* OpenViBE Version 3.5.0: http://openvibe.inria.fr/downloads/

# Installation

Clone the project to a local directory. 

To install the requirements, open a console/command prompt, change to your cloned folder and type:
        pip install -r requirements.txt

Everything from there on is managed directly from the cloned directory.

# Full documentation

Go to docs/index.md for more details!

# License

This software is licensed using BSD 3-Clause. Please refer to LICENSE.md for more details.