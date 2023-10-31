# Installation

**HappyFeat** is available on [PyPI](https://pypi.org/project/happyfeat/) and [GitHub](https://github.com/Inria-NERV/happyFeat).

!!! tip
    Using a [virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) is recommended!
    
## Official version

Releases are published on [https://github.com/Inria-NERV/happyFeat/releases](https://github.com/Inria-NERV/happyFeat/releases)

```shell
        python -m pip install happyfeat
```

## Development version from Github

Clone the project to a local directory:

  - SSH: `git clone git@github.com:Inria-NERV/happyFeat.git`
  - HTTPS: `git clone https://github.com/Inria-NERV/happyFeat` 

To install the requirements, type:

```shell
        python -m pip install -r requirements.txt
```

Everything from there on is managed directly from the cloned directory, most notably in the ```workspace``` folder and subfolders.

!!! warning
    As of today, ***HappyFeat*** requires [OpenViBE 3.5.0](http://openvibe.inria.fr/) to run. A standalone Python version, and support for other BCI softwares are in the works. 
	
!!! note
    Packaging with PyPI and installer .exe file for Windows coming soon...