# Sensor Locations

This page describes how to work with sensor/channel locations (electrode montages, layouts, etc.).

## Setup

When setting up the experimental parameters (see [Getting started](start.md)), a required paremeter is the *Channel Montage*. This is used in the [Visualization](visualize.md) step, to set the correct order of channels in the Frequency/Channel R² map, and to map electrode locations on the scalp in the topographical R² visualization tool.

Two options are available in the drop-down menu:

- "standard" (idealized) montages included in MNE. For more information: [relevant page in MNE documentation](https://mne.tools/dev/auto_tutorials/intro/40_sensor_locations.html)
- "custom" montage, for which the user must provide a CSV file listing the channel names and their respective `[x,y,z]` coordinates.

## Custom coordinates format and example

An example file (`channel_example.txt`) is provided in the repository (folder `tutorials`).

Custom files must follow this format:

```
name,x,y,z
LPA,-86.0761,-19.9897,-47.9860
RPA,85.7939,-20.0093,-48.0310
Nz,0.0083,86.8110,-39.9830
C5,-80.2801,-13.7597,29.1600
C3,-65.3581,-11.6317,64.3580
C1,-36.1580,-9.9839,89.7520
Cz,0.4009,-9.1670,100.2440
C2,37.6720,-9.6241,88.4120
C4,67.1179,-10.9003,63.5800
C6,83.4559,-12.7763,29.2080
T8,85.0799,-15.0203,-9.4900
T10,85.5599,-16.3613,-48.2710
TP9,-85.6192,-46.5147,-45.7070
TP7,-84.8302,-46.0217,-7.0560
CP5,-79.5922,-46.5507,30.9490
CP3,-63.5562,-47.0088,65.6240
CP1,-35.5131,-47.2919,91.3150
...
...
...
```

!!! note
    Nasion (Nz), LPA and RPA channels are optional, but it is strongly recommended to include them nonetheless.
	
!!! warning
    The [visualization tools](visualize.md) using this list of channels & locations (R² map and R² topography) start by comparing the signals' metadata with the provided list (in both custom and standard montages). Displayed channels are the ones present in both lists. Mismatching or missing channels will not be displayed!