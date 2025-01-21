
# Installation

**HappyFeat** is available on [PyPI](https://pypi.org/project/happyfeat/) and [GitHub](https://github.com/Inria-NERV/happyFeat).

!!! warning
    Using a [virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) (e.g. *Miniconda* or *venv*) is **highly** recommended! 
	
!!! warning
	As of version 0.3.0, HappyFeat works with **Python 3.12.8**. 
	
	Using different versions may results in crashes or unhandled errors.
 
## Packaged version

Releases are published on [https://github.com/Inria-NERV/happyFeat/releases](https://github.com/Inria-NERV/happyFeat/releases)

```shell
python -m pip install happyfeat
```

## Development version from Github

Clone the project to a local directory:

  - SSH: `git clone git@github.com:Inria-NERV/happyFeat.git`
  - HTTPS: `git clone https://github.com/Inria-NERV/happyFeat` 

Set up the virtual environment & install the requirements.  
With python venv & pip: 
```shell
python -m venv <yourEnvName>
./<yourEnvName>/bin/activate
python -m pip install -r requirements.txt
```

With conda/miniconda:
```shell
conda env create --name <yourEnvName> -f conda_env.yaml
conda activate <yourEnvName>
```
If you would like to use *Timeflux* with *Happyfeat*:
```shell
python -m pip install timeflux
python -m pip install timeflux_dsp
```

!!! warning
    As of today, ***HappyFeat*** requires [OpenViBE 3.6.0](http://openvibe.inria.fr/) or [Timeflux](https://doc.timeflux.io/en/stable/usage/getting_started.html#installation) to run.
	
!!! note
    Packaging with PyPI and installer .exe file for Windows coming soon...
