# Documentation openvibe-automated-pipeline

Scripts & Qt-based GUI allowing to use BCI pipelines, via OpenViBE standardized scenarios: acquisition & monitoring, feature extraction & selection, classifier training, online classification.

## Key Features

* Automatic generation of scenarios via a GUI. No need to open every scenario in the OpenViBE designer, to set every parameter and triple check everything.
* Easy to use GUI allowing to visualize classification features (R² map, Wilcoxon map, Power Spectral Densities, Time/frequency analysis, Brain Topography), and select features of interest for training a classifier.
* Feature selection and classifier training can be done multiple times in a row, until satisfactory results are achieved. Scenarios are updated automatically. 
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
** packages : shutils / PyQt5 / numpy / MNE / matplotlib / scipy / spectrum / statsmodel / pandas
* OpenViBE Version 3.2.0: http://openvibe.inria.fr/downloads/

# Starter guide

## Generating the scenarios

1. Launch *bcipipeline_qt.py*. 
2. In the drop-down menu of the interface, select the pipeline you want to work with (eg: *Power Spectrum based classification*)
3. Enter the parameters for your experiment: Number of trials, trial length, ... 
  - You can enter a custom list of electrodes (separated with semicolons ;), or provide this list via a .txt file (one electrode name per line)
4. Click **Generate scenarios** when you're ready. 
 
The necessary files for your experiment will be created in the **generated** subfolder.

## Running the experiment

1. Make sure everything is ready for acquiring EEG data! 
  - EEG cap set up
  - plugged to a computer with OpenViBE installed
  - drivers set up in the OpenViBE acquisition server
  - etc.
2. Launch the OpenViBE designer (using *openvibe-designer.cmd* in your install folder).
3. Launch the OpenViBE acquisition server (using *openvibe-acquisition-server.cmd* in your install folder).
  - Connect and run the server  
4. Open the scenario file **sc1-monitor-acq.xml**, created in the previous chapter in the **generated** folder. Click "Run".

The BCI experiment is carried out, with instruction provided on the screen. EEG signals are written to the file **motor-imagery.ov** in the **generated** folder.

## Visualizing & analyzing features, selecting features of interest, training the classifier

1. Open the second scenario, **sc2-extract-select.xml** in **generated**
2. Fast-forward it (double arrow in the OpenViBE designer GUI)
3. Another GUI automatically opens once all the data have been processed. Click **Load Spectrum Files**.
4. Use the different fields & buttons on the left side of the GUI to analyze the EEG data
  - Use *fmin* and *fmax* to plot R2Map and Wilcoxon Map on the frequency region of interest.
  - Visualize the topography for a specific frequency
  - Visualize the PSD & R2 for a specific electrode
5. Select features using the right side of the GUI. 
  - Enter a Electrode;Frequency pair, separated with a semicolon (;). Example: C4;13
  - A frequency range can be entered, using a colon symbol(:) as such: C4;13:16
  - If you want to use more than one feature, click **Add Feature** to add a field. You can remove the last field using **Remove Last Feat**
6. Click **Select features and generate scenarios**. This will generate the scenarios taking care of the classifier training and online classification steps.
7. Click **Run classifier training scenario**.
  - this automatically runs the training in OpenViBE (without GUI), with your selected features.
  - when the training is done, a score (confusion matrix) is displayed
8. If you want to try another set of features, just repeat steps 5 to 7 as many times as needed!

**Note**: you can use this feature selection GUI as a "standalone app", once the scenario **sc2-extract-select.xml** *has been run once*: 
- just run the script **featureExtractionInterface.py**
- the spectral data files needed for analysis are already entered. If you want to use other data, just use the Path1 / Path2 fields.
- **important**: in this use case, you need to browse and find the file **openvibe-designer.cmd** in your OpenViBE installation folder. Otherwise running the classifier scenario won't work.

## Online classification

*coming soon...*
