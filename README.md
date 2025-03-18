# HappyFeat - Interactive framework for clinical BCI applications

[![docs status](https://readthedocs.org/projects/happyfeat/badge/?version=latest)](https://happyfeat.readthedocs.io/en/latest/) [![test: status](https://github.com/Inria-NERV/happyFeat/actions/workflows/test.yaml/badge.svg)](https://github.com/Inria-NERV/happyFeat/actions/workflows/test.yaml) [![PyPI version](https://img.shields.io/pypi/v/happyfeat.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/happyfeat/)  [![License: BSD-3](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](https://spdx.org/licenses/MIT.html) 

HappyFeat is a software aiming to to simplify the use of BCI pipelines in clinical settings. More precisely, it is a **software assitant for extracting and selecting classification features for BCI**.

[Get started!](https://happyfeat.readthedocs.io/en/latest/)

It gathers all necessary manipulations and analysis in a single convenient GUI, and automates experimental or analytic parameters. The resulting workflow allows for effortlessly selecting the best features, helping to achieve good BCI performance in time-constrained environments. Alternative features based on Functional Connectivity can be used and compared or combined with Power Spectral Density, allowing a network-oriented approach. 

It consists of Qt-based GUIs and Python toolboxes, allowing to realize all steps for customizing and fine-tuning a BCI system: feature extraction & selection, classifier training.

HappyFeat also allows to interface with BCI softwares (OpenViBE for the moment!) in order to facilitate the whole BCI workflow, from data acquisition to online classification.

The focus is put on ease of use, trial-and-error training of the classifier, and fast and efficient analysis of features of interest from BCI sessions.

## Key Features

* **Easy to use GUI** allowing to extract and visualize classification features, and select the most relevant ones for training a classifier.
* Use **Spectral Power** or **Coherence-based** features for classification. HappyFeat allows to extract & visualize both types of features in parallel, and **mix them at the training level**.
* Feature selection and classifier training can be done multiple times in a row, until satisfactory results are achieved.
* A **worspace management system** keeps tracks of all extraction- and training-related manipulations, and enables a high degree of reproducibility.

# Requirements

* Python 3.12.8
* Python packages : shutils / PySide6 / numpy / MNE / matplotlib / scipy / spectrum / statsmodel / pandas
* OpenViBE Version 3.6.0: http://openvibe.inria.fr/downloads/
* ... or [Timeflux](https://timeflux.io)

# Installation & Full documentation

HappyFeat is available as a [package on PyPi](https://pypi.org/project/happyfeat/). Otherwise, you can clone this repository.

Go to [https://happyfeat.readthedocs.io/en/latest/](https://happyfeat.readthedocs.io/en/latest/) for more details.

# License

This software is licensed using BSD 3-Clause. Please refer to LICENSE.md for more details.
