# Extraction parameters

This page lists and explains parameters used in the [feature extraction](extract.md) step of HappyFeat.

!!! note
	Some parameters are only available with specific pipelines. More can be added in the future.

## General

- **Epoch of interest (EOI) (s)**:

	Length of the trials, in seconds. 

- **EOI offset (s)**:

	Delay between the stimulation triggering the trial, and the start of the time window considered for our processing, in seconds.	This can be useful to account for reaction times.

- **Frequency resolution (ratio)**:

	Ratio between the sampling frequency of the signals, and the FFT size used for spectral estimation. 
	
	$$
	FFT Size = \frac{Freq. Sampling}{Freq. Resolution}
	$$
	
	Lower values give higher frequency resolution, but computing times are increased (significantly when using Connectivity).
	
	Ex: F.Res. = 1, FFT size = Sampling freq. In that case, each freq. "bin" = 1 Hz.
	
	Ex: F.Res. = 2, FFT size = Sampling freq. / 2. In that case, each frequency "bin" =  2 Hz.
	
	Ex: F.Res. = 0.5, FFT size = Sampling freq. * 2. In that case, each frequency "bin" = 0.5 Hz.


## PSD

As of version 0.3.0, HappyFeat uses the Burg Auto-Regressive method for spectral estimation when using OpenViBE, and Welch's method when using Timeflux. More estimation methods and flexibility will be added in future versions.  

With both methods, spectral estimation is performed (during [extraction](extract.md)) on sliding windows of signal, within Epochs of Interest (defined earlier). These estimations are then averaged across all windows when performing the [statistics visualizations](visualize.md), and used for [training a classifier](train.md).

For a comparison of both methods in the context of EEG/BCI, see this [article by Diez et al.](https://www.researchgate.net/publication/23932037_A_Comparative_Study_of_the_Performance_of_Different_Spectral_Estimation_Methods_for_Classification_of_Mental_Tasks).

- **Sliding window (PSD) (s)**
    
    Length of the window used for spectral estimation, in seconds.

- **Window Shift (PSD) (s)**
    Shift between 2 consecutive windows of spectral estimation, in seconds.
        
- **Auto-regressive estimation length (s)**

    Order of the auto-regressive model, in seconds. Higher orders give more spectral resolution, but increase computation times. This can be computed with the formula:
    
    $$
    {AR order}_{s} = \frac{AR order}{Freq. sampling} 
    $$

    **In pipelines computing both PSD and Connectivity, this parameter is shared **.

!!! note
    A model order value too high may result in reduced spectral estimation quality: high influence of noise, spurious peaks, etc.
    Different criteria exist to determine model orders (e.g. [AIC and BIC](https://medium.com/@jshaik2452/choosing-the-best-model-a-friendly-guide-to-aic-and-bic-af220b33255f)). Good values to start with are 15 to 25 (with a sampling frequency of 500Hz, this corresponds to 0.03s and 0.05s)

## Connectivity

As of version 0.3.0, Connectivity estimation is only available with OpenViBE. It uses a bi-variate variation of Burg's auto-regressive spectral estimation method. [Reference (Schlögl & Supp)](https://pub.ista.ac.at/~schloegl/publications/schloegl+supp2006.pdf)    

As for PSD, it is performed (during [extraction](extract.md)) on sliding windows of signal, within Epochs of Interest (defined earlier). A connectivity matrix of dimension $(nb.freq. \times nb.channels \times nb.channels)$ is computed for each window, then converted to an Average Node Strength matrix by averaging values across one of the $nb.channels$ dimension. This Average Node strength matrix is of dimension $(nb.freq. \times nb.channels)$, similar to PSD estimations.

These estimations are then averaged across all windows when performing the [statistics visualizations](visualize.md), and used for [training a classifier] (train.md).

- **Connectivity estimator**

    The [coherence](https://en.wikipedia.org/wiki/Coherence_(signal_processing))-based estimator to compute. Choices are:
    
    - Coherence: the square-root of Magnitude Square Coherence, defined for two $x$ and $y$ signals at frequency $f$ as (with $C_{xy}$ the cross-spectral density for $x$ an $y$, and $P_{xx}$ the power spectral density for signal $x$):
    
    $$
    Coh_{xy}(f) = \sqrt{\frac{|C_{xy}(f)|^2}{P_{xx}(f).P_{yy}(f)}}
    $$
    
    - Absolute imaginary part of coherence, defined for two $x$ and $y$ signals at frequency $f$ as (with $C_{xy}$ the cross-spectral density for $x$ an $y$, and $P_{xx}$ the power spectral density for signal $x$):
    
    $$
    AbsImCoh_{xy}(f) = \frac{Im(C_{xy}(f))}{\sqrt{P_{xx}(f).P_{yy}(f)}}
    $$

- **Sliding Window (connect.) (s)**

    Length of the window used for the connectivity estimation, in seconds.

- **Window overlap (connect.) (%)**

    Percentage of overlap between two consecutive estimation windows.
    
    Ex: with windows of 0.5s and 20% of overlap, two consecutive windows share 0.1s of data, and the second window starts ("shifts") 0.4s after the first one.  
    
- **Auto-regressive estimation length (s)**

    *See above, in the PSD part*

## Next up... 
