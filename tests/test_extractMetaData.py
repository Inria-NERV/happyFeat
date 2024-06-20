from happyfeat.lib.extractMetaData import *
import pandas as pd
import numpy as np

# Unit tests for extractMetaData.py

def test_extractMetadata():
    sampFreq, electrodeList = extractMetadata("tests/data/testdata_extractMetaData.csv")
    expected_sampFreq = 500
    expected_electrodeList = ["Fp1", "Fz", "F3", "F7", "FT9", "FC5", "FC1", "C3", "T7", "TP9", "CP5", "CP1", "Pz", "P3",
                              "P7", "O1"]
    assert expected_sampFreq == sampFreq
    assert expected_electrodeList == electrodeList

# TODO:
# find a way to test generateMetadata(), which uses OV...
