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
