from mne.datasets import eegbci
from pathlib import Path

customPath = str(Path.cwd())
raw_fnames = eegbci.load_data(subjects=[1], runs=[4, 8, 12], path=customPath)

