# Extraction parameters

This page lists and explains parameters used in the [feature extraction](extract.md) step of HappyFeat.

!!! note
	Some parameters are only available with specific pipelines. More can be added in the future.

## General

- **Epoch of interest (EOI) (s)**:

	Length of the trials, in seconds. 

- **EOI offset (s)**:

	Delay between the stimulation triggering the trial, and the start of the time window considered for our processing, in seconds.
	
	This can be useful to account for reaction times.

- **Frequency resolution (ratio)**:

	Ratio between the sampling frequency of the signals, and the FFT size used for spectral estimation. 
	
	$$
	FFT Size = \frac{Freq. Sampling}{Freq. Resolution}
	$$
	
	Lower values give higher frequency resolution, but computing times are increased (significantly when using Connectivity).
	
	Ex: F.Res. = 1, FFT size = Sampling freq. In that case, each freq. "bin" = 1 Hz.
	
	Ex: F.Res. = 2, FFT size = Sampling freq. / 2. In that case, each frequency "bin" =  2 Hz.
	
	Ex: F.Res. = 0.5, FFT size = Sampling freq. * 2. In that case, each frequency "bin" = 0.5 Hz.


## PSD-related

- **Sliding window (PSD) (s)**

- **Window Shift (PSD) (s)**

- **Auto-regressive estimation length (s)**

## Connectivity-related

- **Connectivity estimator**

- **Sliding Window (connect.) (s)**

- **Window overlap (connect.) (%)**

- **Auto-regressive estimation length (s)**


<center><img src="../../img/hf_gui_new_extract.png" alt="HappyFeat main GUI, Extraction part highlighted" style='object-fit: contain;'/></center>


## Next up... 