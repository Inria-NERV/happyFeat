
# Tutorial using Timeflux

This tutorial showcases the main mechanisms of ***HappyFeat***, using **Timeflux** as a processing engine, and EEG data from the *[Physionet](https://physionet.org/content/eegmmidb/1.0.0/)* dataset, loaded using *[MNE](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html)*.

Make sure to follow the steps in the [Installation](install.md) page first. Also, make sure *Timeflux* is installed in your environment:
```shell
python -m pip install timeflux
python -m pip install timeflux_dsp
```
## Creating and setting up a workspace 

First, browse for the folder in which you would like **HappyFeat** to create and look for workspaces. This will be referred to as `<workspaces>`

Click on "Start new workspace" and enter a name for your workspace. This will be referred to as `<newWorkspace>`.

```shell
						insert figure
```


A new assistant GUI will open, allowing you to set up the BCI experiment parameters. 
- In the first drop-down menu, select **Timeflux** as a BCI platform.
- In the second drop-down menu, select **Graz BCI - Power Spectrum Features (2 Classes)**. This corresponds to the metric used in this workspace, and the associated data processing pipelines.
- In the **Channel Montage** drop-down menu, select `Custom`, then browse to select this file :
`<happyfeatInstallFolder>/tutorials/electrodes_list_64_physionet.txt`
- You may leave the default values for the following parameters (nb trials per class, stimulation 1/2, etc.).
- Click on `Generate and launch HappyFeat` to proceed.

```shell
						insert figure
```

## Loading data from Physionet
In a terminal, navigate to **HappyFeat**'s installation folder, then type:
```shell
python tutorials/physionetTutorial.py
```
This will download 3 EDF signal files to the folder: `<happyfeatInstallFolder>/MNE-eegbci-data/files/eegmmidb/1.0.0`

Copy those files to your new workspace's `signals` folder:
```shell
cp <happyfeatInstallFolder>/MNE-eegbci-data/files/eegmmidb/1.0.0/*.edf <workspaces>/<newWorkspace>/signals
```
The files should appear in the list in the left pannel of the application (**Feature Extraction**).

```shell
						insert figure
```

## Extracting the features

Before extracting features from our EDF files, we still have a few things to set up.
Click on the `Extraction` menu in the top bar, and `Set Class Stimulations`. Enter **`T2;T0`** and validate.

!!! note
	Those are the trigger names in the EDF files for the Physionet dataset. T0 corresponds to the onset of a "Rest" trial, and T2 to a "imagine Right Hand movement" trial.

Then, in the `Extraction Parameters`, set `Epoch of Interest (EOI) (s)` to 3, and leave the default values for other parameters.

Select the 3 files in the list, and click **`Extract Features and trials`**.

## Visualizing the extracted features
