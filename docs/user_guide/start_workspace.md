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