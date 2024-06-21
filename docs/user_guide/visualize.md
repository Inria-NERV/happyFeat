# Using HappyFeat

## Visualizing & analyzing features (central panel)

This step allows to visualize spectral features in many ways, in order to help selecting sensors and frequency bands of interest.

The top list of this panel is updated with signals/runs which have undergone [feature extraction](extract.md), using the current set of extraction parameters (see paragraph on *sessions* in [workspaces](workspaces.md))

In this list, select the runs you wish to analyze. When multiple runs are selected, all trials from those runs will be accumulated when computing the different statistics.

Click **"Load spectrum file(s) for analysis"**

Use the buttons to display the plots you need, and the parameter fields to adapt the visualizations.


!!! tip
    *You can display as many visualization windows as needed, with different parameters.*
	
### Frequency/Channels R² contrast map

*description coming soon...*

### R² as a scalp topographic map

*description coming soon...*

### Direct comparison of metrics

*description coming soon...*

### Time/frequency ERD/ERS analysis

*description coming soon...*

### Note on sensor montages

!!! warning
    The R² map and R² topography are able to display an orderer list of channels and their locations thanks to the montage (standardized or custom) provided by the user when [setting up the experimental parameters](start.md). They both start by comparing the signals' metadata with the provided sensor list (in both custom and standard montages). Displayed channels are the ones present in both lists. Mismatching or missing channels will not be displayed!


### Automatic feature selection

See [dedicated page](autofeat.md).


## Next up... [Training the classifier](train.md)