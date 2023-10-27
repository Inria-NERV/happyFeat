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