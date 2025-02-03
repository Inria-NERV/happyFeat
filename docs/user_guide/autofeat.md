# Using HappyFeat

## Automatic Feature Selection 

Version 0.2.0 of HappyFeat introduces the "AutoFeat" mechanism, helping to automatically select features after [**Extraction**](extract.md) and [**loading files for Visualization**](visualize.md).


This is realized by clicking on the button "*Auto. select optimal features*".

The three "best" features (meaning the channel/frequency pairs with the highest R² values) are automatically selected and entered in the Training part, in the rightmost panel.

A subset of channels and frequencies can be determined using the top menu options:  "*Feature Autoselect*". 

The R² map corresponding to this subset can be visualized using the button "*R² map (sub select.)*"

<center><img src="../../img/hf_gui_autofeat.png" alt="HappyFeat main GUI, Extraction part highlighted" style='object-fit: contain;'/></center>

!!! note
    More flexibility with this mechanism (e.g. number of features extracted, metric of selection, etc.) will be included in future versions of *HappyFeat*.