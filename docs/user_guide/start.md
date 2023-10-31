# Getting started

!!! warning
    As of today, ***HappyFeat*** requires [OpenViBE 3.5.0](http://openvibe.inria.fr/) to run. A standalone Python version, and support for other BCI softwares are in the works. 
	
The application's entry point is the Python script *happyfeat_welcome.py*. Just type the following:

```shell
    python happyfeat_welcome.py
```

This script launches a GUI allowing to select a **[workspace](workspaces.md)**. You can browse for location of your choice, choose from a list of existing **workspace**, or create a new **workspace**.

<center><img src="../../img/hf_gui1.png" alt="HappyFeat workspace selection GUI" style='height: 50%; width: 50%; object-fit: contain;'/></center>

## Setting up a new workspace

Click on "Start new workspace" and enter a name for your workspace. A new assistant GUI will open, allowing you to set up the BCI experiment parameters. 

<center><img src="../../img/hf_gui2.png" alt="HappyFeat BCI pipeline assistant GUI" style='height: 50%; width: 50%; object-fit: contain;'/></center>

In the "Protocol Selection" drop-down menu, select the metric(s)/feature(s) you want to work with (eg: `Power Spectrum based classification`).
As of today, you can choose between **Power Spectral Density**, **Connectivity-based Node Strength**, or **mixing both**.

Then, enter the parameters for your experiment: Number of trials, trial length, etc.

You can either use known channel montages (e.g. `standard 1020`) or a custom montage. See the [specific page on montages](montage.md) for more information.

You also need to browse for the **OpenViBE** designer application on your computer (either the .exe, .sh or .cmd file).

Click on `Generate scenarios & Launch HappyFeat` when you're ready. 
 
From there on, files & folders will be located in the `<happyfeat_install>/workspace/<myworkspacename>` subfolder, 
and all information and configuration will be managed in the `<happyfeat_install>/workspace/<myworkspacename>.hfw` file.

## Loading an existing workspace

You can find the list of existing *workspaces* in the *happyfeat_welcome.py* GUI. Select one and click on "Load existing workspace". All previously handled parameters, results, and working files are loaded.

Note that workspaces can be shared from one computer to another, by simply copying the workspace's folder and configuration file.