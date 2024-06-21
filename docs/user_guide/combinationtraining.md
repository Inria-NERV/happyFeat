# Using HappyFeat

## Combination Training

Version 0.2.0 of *HappyFeat* introduces a new mechanism, allowing the user to automatically try multiple combinations of training features, in order to find the one with the best score without having to manually change the training features.

Clicking "*Train - Find best comb.*" with multiple training features launches multiple training attempts depending on the feature types, as such:

- if one feature type is used (PSD of Connectivity alone), it tries [*feat1*], [*feat1*+*feat2*], [*feat1*+*feat2*+*feat3*]...
- if two feature types are used (PSD+Connectivity), it tries [*feat1PSD* + *feat1Connect*], [*feat1PSD*+*feat2PSD* + *feat1Connect*+*feat2Connect*]...

!!! note
    More ways of combining features will be included in future versions of *HappyFeat*.
	