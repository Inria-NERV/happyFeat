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
  * *Functional Connectivity (coming soon!)*
* Available classifiers:
  * LDA
  * *more coming soon!*

* *Coming soon : More Features!*
  * *Functional Connectivity pipeline*
  * *More feature classes, more classification algos*
  * *Particle swarm algorithm for determining optimal AutoRegressive model order*

# Requirements

* Python 3.9 or more recent
* Python packages : shutils / PyQt5 / numpy / MNE / matplotlib / scipy / spectrum / statsmodel / pandas
* OpenViBE Version 3.3.0: http://openvibe.inria.fr/downloads/

# Starter guide

## Installation

Clone the project to a local directory. 

To install the requirements, open a console/command prompt, change to your cloned folder and type:
        pip install -r requirements.txt

Everything from there on is managed directly from the cloned directory.

## Generating the scenarios

1. Launch *1-bcipipeline_qt.py*
2. In the drop-down menu of the interface, select the pipeline you want to work with (eg: *Power Spectrum based classification*)
3. Enter the parameters for your experiment: Number of trials, trial length, ...
  - You can enter a custom list of electrodes (separated with semicolons ;), or provide this list via a .txt file (one electrode name per line)
  - Note that this list of electrodes should correspond to the EEG setup you're using!
4. Click **Generate scenarios** when you're ready. 
 
The necessary files for your experiment will be created in the **generated/** subfolder.

## Running the experiment

1. Make sure everything is ready for acquiring EEG data! 
  - EEG cap set up
  - plugged to a computer with OpenViBE 3.2.0 installed
  - drivers set up in the OpenViBE acquisition server
  - etc.
2. Launch the OpenViBE designer (using *openvibe-designer.cmd* in your install folder).
3. Launch the OpenViBE acquisition server (using *openvibe-acquisition-server.cmd* in your install folder).
  - Connect and run the server  
4. Open the scenario file **generated/sc1-monitor-acq.xml**, created in the previous step. Click "Run".

The BCI experiment is carried out, with instruction provided on the screen. EEG signals are written in **generated/signals/**, with a filename indicating date and time of the acquisition.

## Using the offline processing interface

Launch *2-featureExtractionInterface.py*. A GUI with 3 panels opens, allowing you to manipulate and analyse acquired EEG signals.

### Extract the features 

This step allows to extract the data we need to analyse the spectral features and select them for training the classifier.

1. In the left panel of the GUI is shown the list of available experimental runs of EEG signals. Select one or multiple sessions you're interested in analyzing.
2. Enter the extraction parameters (Epoch of interest, epoch offset from stimulation, autoregressive model order...)
3. A list of (non-editable) experimental parameters is provided as a reminder. 
4. Make sure you've set the path to the OpenViBE designer (*openvibe-designer.cmd*, in your OpenViBE install folder)
5. Click on **"Extract Feature and Trials"**. This might take a moment...
6. Runs for which the extraction step has been performed, and that are available for visualization & training, appear in the lists of the central and right part of the GUI.

Important notes:
- The list of sessions available for analysis/training (central and right parts) are **reset** if you click **Extract** after modifying the parameters!
- If you want to extract from multiple runs/sessions with the same parameters, you can do it in one go (by selecting more than one session in the list), or in successive step. This may be useful to gain time during the acquisition process, as you can extract data from the previous run while acquiring a new one.

### Visualizing & analyzing features

This step allows to visualize spectral features in many ways, in order to help selecting sensors and frequency bands of interest.

1. In the central panel of the GUI, select session(s) you wish to analyse.
2. Click **"Load spectrum file(s) for analysis"**
  - *Note: when using multiple sessions/runs, the visualizations are computed using all trials in selected sessions.*
3. Use the buttons to display the plots you needs, and the parameter fields to adapt the visualizations.
  - *Note: you can display as many visualization windows as needed, with different parameters.*

### Selecting features of interest, training the classifier

This step allows to train the classification algorithm, using sub-sets of sensors and frequencies. All 

1. In the right part of the GUI, first select sensor/frequency pairs:
  - Use this format: **Electrode;Frequency** separated with a semicolon (;). Example: **C4;13**
  - A frequency range can be entered, using a colon symbol(:) as such: **C4;13:16**
  - If you want to use more than one feature, click **Add Feature** to add a field. 
  - You can remove the last field using **Remove Last Feat**
2. Enter the number of k-fold partitions you want to use for the training step. The trials used for training will be segmented using this number of partitions.
3. Select the session(s) you want to use for training in the list.
4. Two options are available for training the classifier:
  - **Concatenate trials from all selected runs**. For this option, click on **TRAIN CLASSIFIER**. The classification algorithm will be trained using all trials from selected runs. At the end of the process, a classification score is displayed, and the Online/Testing scenario is automatically updated with the classifier weights and the selected sensor/frequency pairs.
  - **Find the best combination of runs**. For this option, click on **FIND BEST COMBINATION**. The classification algorithm will be trained multiple times, on a composite session created by concatenating trials, for all possible combination of the selected runs. For example, if the runs are labeled A, B, and C, combinations tested will be \[A, B, C, AB, AC, BC, ABC]. Scores for all combinations are displayed, and the Online/Testing scenario is automatically updated with the classifier weights *from the best scoring combination* and the selected sensor/frequency pairs.

Important notes:
  - This process can be run as many times as needed. Every time it is run, the scenario for the Online/Testing part of the experiment will be updated.
  - A maximum number of 5 scenarios can be selected for the combinations algorithm, as the number of combinations to test (and duration of process) becomes too high...
  - Training the classifier is done using OpenViBE in the background (without GUI). 

## Online classification / Testing step

1. Make sure everything is ready for acquiring EEG data! (same as Acquisition step...)
2. Make sure the OpenViBE acquisition server is running.
3. Open the scenario file **generated/sc3-online.xml**.
  - Note: the classifier weights and pairs of channels+frequencies are automatically updated using the Offline GUI. See previous steps!
4. Click "Run". Instructions are provided to the user, along with visual feedback on the classification performance.
6. EEG data is recorded in **generated/signals/motor-imagery-live.ov** for replay purposes.
