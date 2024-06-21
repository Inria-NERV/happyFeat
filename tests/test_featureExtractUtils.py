from happyfeat.lib.featureExtractUtils import *
import pandas as pd
import numpy as np

# Unit tests for featureExtractUtils.py

def test_psdSizeToFreqRes():
    expected = 1.0
    actual = psdSizeToFreqRes(512, 512)
    assert actual == expected, "psdSizeToFreqRes returned an incorrect value"
    expected = 2.0
    actual = psdSizeToFreqRes(256, 512)
    assert actual == expected, "psdSizeToFreqRes returned an incorrect value"

def test_freqResToPsdSize():
    expected = 256
    actual = freqResToPsdSize(2.0, 512)
    assert actual == expected, "freqResToPsdSize returned an incorrect value"
    expected = 512
    actual = freqResToPsdSize(1.0, 512)
    assert actual == expected, "freqResToPsdSize returned an incorrect value"

def test_samplesToTime():
    expected = 1.0
    actual = samplesToTime(512, 512)
    assert actual == expected, "samplesToTime returned an incorrect value"
    expected = 0.25
    actual = samplesToTime(128, 512)
    assert actual == expected, "samplesToTime returned an incorrect value"

def test_timeToSamples():
    expected = 128
    actual = timeToSamples(0.25, 512)
    assert actual == expected, "timeToSamples returned an incorrect value"
    expected = 1024
    actual = timeToSamples(2.0, 512)
    assert actual == expected, "timeToSamples returned an incorrect value"

def test_load_csv_np():
    header, data = load_csv_np("tests/data/testdata_load_csv_np.csv")
    with open("tests/data/testdata_load_csv_np_refheader.csv", "r") as refheader:
        assert refheader.read().split(',') == header.tolist(), "load_csv_np failed: mismatch in header"
    refdata = np.loadtxt("tests/data/testdata_load_csv_np_refdata.csv", dtype=float, delimiter=',')
    print(refdata)
    assert refdata.all() == data.all(), "load_csv_np failed: mismatch in data"

# TODO :
# Extract_CSV_Data
# Extract_Connect_CSV_Data
# Extract_Connect_NodeStrength_CSV_Data