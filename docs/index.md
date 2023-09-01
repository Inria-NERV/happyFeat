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

# Getting started

The application's entry point is the Python script *happyfeat_welcome.py*.	

This script launches a GUI allowing to start a new *workspace*, or to choose from a list of existing *workspaces*.

## Workspaces

In order to keep track of parameters used for acquisition and feature extraction 
but also results from classification training attempts, HappyFeat uses a system of *workspaces* and *sessions*.

Workspaces are managed in the folder *<HappyFeat_install>/workspace>*. They consist of a configuration file 
(such as *<HappyFeat_install>/workspace/myWorkspace.hfw*) and a folder with the same basename (such as 
*<HappyFeat_install>/workspace/myWorkspace).

The configuration file contains all useful information, parameters, and manipulations (extractions, training attempts) that have 
been realised since the creation of the workspace. It uses the JSON format, which is easily manipulated and human-readable.

The associated folder contains:
- OpenViBE scenarios relevant to the ongoing analysis, using user-defined parameters which are set in HappyFeat's GUIs. These are 
not meant to be manipulated by the user, as they are automatically generated and modified along the differents processing steps of HappyFeat, 
but can nonetheless be loaded in the OpenViBE designer for verification purposes.
- a *signals* folder, in which EEG signals of interest are stored (either directly from acquisitions when using HappyFeat in a real life 
experiment, or copied/pasted from an existing database in the case of offline analysis)
- a *sessions* folder, containing files obtained from the processing steps of HappyFeat (feature extraction, training attempts...) and used by 
the software for further analysis or displaying results.

### HappyFeat's extraction & training "sessions"

Along with *workspaces*, HappyFeat uses *sessions* to manage extractions & training attempts and keep track of everything.

A *session* is a set of extraction parameters, and is defined by:
- intermediate working files generated during feature extraction, using this set of parameters,
- training attempts & their results, once again using this set of parameters.

*Sessions*' information are kept in the workspace's configuration file. Working files are managed in the 
*<currentWorkspace>/sessions/<number>* folder (each numbered folder corresponding to a *session*). 

### Managing Workspaces

Users may create and manage workspaces in any way they find fitting. However, we strongly advise to use one workspace 
per set of EEG signal files. A few examples:
- one workspace = one experimental session made up of multiple EEG runs acquired the same day with the same subject, 
- one workspace = all EEG runs for one subject, across multiple days
- one workspace = a set of signal files (or runs) from previous acquisitions, all gathered together to test & compare different metrics

This allows to efficiently organize BCI experiments, avoiding mix-ups between files and other mistakes...

## Setting up a new workspace

If you are using HappyFeat for the first time, click on "Start new workspace" and enter a name for your workspace. A new GUI will open, allowing you to set up the BCI experiment parameters. 

In the "Protocol Selection" drop-down menu, select the metric(s)/feature(s) you want to work with (eg: *Power Spectrum based classification*).
As of today, you can choose between Power Spectral Density, Connectivity-based Node Strenght, or using both.

Then, enter the parameters for your experiment: Number of trials, trial length, etc.

You can either use known channel montages (e.g. *standard 1020*) or a custom montage. In that case, 
you will be prompted to provide a description via a .txt file.

You also need to browse for the OpenViBE designer application on your computer (either the .exe, .sh or .cmd file).

Click **Generate scenarios & Launch** when you're ready. 
 
From there on, files & folders will be located in the **<happyfeat_install>/workspace/<myworkspacename>** subfolder, 
and all information and configuration will be managed in the **<happyfeat_install>/workspace/<myworkspacename>.hfw** file;

## Loading an existing workspace

You can find the list of existing *workspaces* in the *happyfeat_welcome.py* GUI. Select one and click on "Load existing workspace". 
All previously handled parameters, results, and working files are loaded.

Note that workspaces can be shared from one computer to another, by simply copying the workspace's folder and configuration file.

# Using HappyFeat

After starting or loading a workspace, *HappyFeat*'s main GUI is launched. It is made up of three parts, spread out in 
three panels: **Feature Extraction**, **Feature Visualization** and **Classifier Training**.

## Extracting the features (left panel)

This step allows to extract relevant data from EEG signals, before using this data to analyse the 
spectral/connectivity features and select them for training the classifier.

Available signal files are shown in the top list of this panel. This list is automatically updated from the *signals* folder 
of the current workspace. You can either manually add signal files (in OpenViBE's **.ov** format), or use the generated OpenViBE 
scenario **sc1-monitor-acq.xml** in the current workspace folder, if in the context of a BCI experiment. This scenario is 
set up to write EEG signal files in the correct folder.

From this list, select one or multiple signal files you're interested in analyzing. Enter the extraction parameters 
(Epoch of interest, epoch offset from stimulation, autoregressive model order...). A list of (non-editable) 
experimental parameters (set up when creating the workspace) is provided as a reminder.

Click on **"Extract Feature and Trials"**. 

	*- Note that processing times are highly dependent on the extraction parameters and the selected metric. As a rule of thumb, Connectivity 
	is much slower to compute than PSD, and using a higher AR order and/or higher number of estimations (shorter windows, higher amount of 
	overlap) means longer processing time.*

EEG signal files (or **runs**) for which the extraction step has been performed and that are therefore available 
for visualization & training, appear in the lists of the central and right part of the GUI.


#### Switching between sessions

Changing **any** parameter in the extraction panel and clicking on the "Update" or the "Extract" button will switch 
to another *session*. HappyFeat automatically detects if the new set of parameters has already been used before. 
If not, a new *session* is created (meaning a new entry in the *workspace*'s configuration file, and a new numbered folder in the 
file tree). Otherwise, all the info from the session is recovered and made available.

The "update" button switches to another (existing or new) session, without launching any extraction. This allows for example to 
quickly compare training results using different connectivity estimators (coherence vs. imaginary coherence), or using different AR model orders.

#### Avoiding redundant operations

When launching a "Feature Extraction" operation, HappyFeat automatically checks if the selected EEG signal files have already been processed 
using the parameter set of the current session. If it's the case, the user is asked if they want to renew the operation. 


### Visualizing & analyzing features (central panel)

This step allows to visualize spectral features in many ways, in order to help selecting sensors and frequency bands of interest.

The top list of this panel is updated with signals/runs which have undergone feature extraction, using the current set of extraction 
parameters (see paragraph on *sessions*)

In this list, select the runs you wish to analyze. If selecting multiple runs, all trials from selected runs will be considered when computing the different statistics.

Click **"Load spectrum file(s) for analysis"**

Use the buttons to display the plots you need, and the parameter fields to adapt the visualizations.
  - *Note: you can display as many visualization windows as needed, with different parameters.*

### Feature Selection & Training the Classifier (right panel)

This step allows to train the classification algorithm, using sub-sets of sensors and frequencies.  

First, select sensor/frequency pairs:
  - Use this format: **Electrode;Frequency** separated with a semicolon (;). Example: **C4;13**
  - A frequency range can be entered, using a colon symbol(:) as such: **C4;13:16**
  - If you want to use more than one feature, click **Add Feature** to add a field. 
  - You can remove the last field using **Remove Last Feat**
  - *Note: If you have setup your workspace to allow for using two metrics, you can choose to use training features for only one of the metrics or for both metrics* 

The number of k-fold partitions to use for the training step can be set. Trials used for training will be segmented using this number of partitions.

The list of runs available for training is updated with runs which have undergone feature extraction in this *session* 
(see paragraph on *sessions* for more info)

Select the run(s) you want to use for training in the list. Trials from all selected runs are considered ("concatenated") for the following training attempt.

Click on "Train classifier". After processing, a detailed report of accuracies is provided in a pop-up window, 
and a shorter summary is made available in the bottom part of this panel.
Results from all training attempts of the current *session* are listed.

This process can be run *as many times as needed*. Every time it is run, the scenario for the Online/Testing (*sc3-online.xml*) part of the experiment will 
be updated with selected features and computed classifier weights. **Note** that this scenario is updated with the features & weights from the *last* training 
attempt, not necessarily the best one! To make sure it contains the features/weights you want, you need to re-run a training attempt with those.
  
For a given *session*, each training attempt is numbered, and the computed classifier weights can be found in 
*<happyfeat_install>/<currentWorkspace>/sessions/<sessionNb>/train/classifier-weights-<nb>.xml* 


# Using HappyFeat in a BCI experiment

A BCI experiment consists of three steps:
- signal acquisition using EEG hardware
- signal analysis (realized using HappyFeat's main GUI)
- online BCI with trained classifier, using EEG hardware

Steps 1&3 are also facilitated by HappyFeat. This section describes how to interface with EEG acquisition systems.
 
## Step 1: Acquisition

### Setting up the experiment

1. Make sure everything is ready for acquiring EEG data! 
  - EEG cap set up
  - plugged to a computer with OpenViBE 3.5.0 installed
  - drivers set up in the OpenViBE acquisition server
  - etc.
2. Launch the OpenViBE designer (using *openvibe-designer.cmd* (or .exe or .sh) in your install folder).
3. Launch the OpenViBE acquisition server (using *openvibe-acquisition-server.cmd* (or .exe or .sh) in your install folder).
  - Connect and run the server  
4. Run *happyfeat_welcome.py*, and either start a new workspace or select an existing one.
5. In your workspace folder, open the scenario file **sc1-monitor-acq.xml**.

**Note**: as explained in the *Workspaces* section, we strongly advise to create one workspace per experiment.

**Note**: the BCI experiment sequencing is set up in the *mi-stimulations.lua* script. Please refer to the tutorials 
on the OpenViBE website to learn how to fine tune your BCI experiment.

### Data Acquisition

When you are ready, click "Run" in the OpenViBE designer. The BCI experiment is carried out, with instruction provided on the screen. 
EEG signals are written in the **signals** folder of your current workspace, with a filename indicating date and time of the acquisition.

## Step 3: Online classification / Testing

1. Make sure everything is ready for acquiring EEG data! (same as Acquisition step...)
2. Make sure the OpenViBE acquisition server is running.
3. In your workspace folder, open the scenario file **sc3-online.xml**.
  - *Note: the classifier weights and pairs of channels+frequencies are automatically updated using HappyFeat's main GUI. See previous steps!*
4. Click "Run" in the OpenViBE designer. Instructions are provided to the user, along with visual feedback on the classification performance.
5. EEG data is recorded in the **signals** folder for replay purposes.

**Note**: the BCI experiment sequencing is set up in the *mi-stimulations.lua* script. Please refer to the tutorials 
on the OpenViBE website to learn how to fine tune your BCI experiment.





