"""this should take high pass brain files (or other brain files) and add a nan 
timepoint for the timepoints that were dropped with splitting tiff files into niis"""


import functions as fun

import os
import sys
import numpy as np
import argparse
import subprocess
import json
import time
import nibabel as nib
import h5py
import ants
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
import brainsss
import scipy as scipy
from scipy.signal import find_peaks
from matplotlib import pyplot as plt
import math
from xml.etree import ElementTree as ET
import csv as csv
from sklearn.decomposition import IncrementalPCA


def main(args):
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']


    ##first identify if it should be every 500 or every 1000 timepoint that is reinserted
    #1. look for channel_1_s500.nii in directory if it is there then evry 500 if not then every 1000

    #insert timepoint of shape brain (x,y,z,1) with zeros or nans...
    # consdiering zeros because then I don't have to worry about dealing with nans for mean and std
        #shouldn't impact the mean too much and should roughly be consistent
        #HOWEVER when averaging across trials that could mess it up
        # => nans are better
        #would it be better to just remove the timepoints?