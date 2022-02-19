## take moco h5py file and run zscore on it and output another h5py file
## currently using all different h5py files because it seems easier to keep it organized, but all the data could be added to the same file with different keys

## this is currently set to run each volume independently

import os
import sys
import numpy as np
import argparse
import subprocess
import json
from time import time
import nibabel as nib
import brainsss
import h5py
import ants

def main(args):

    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    #file_names = args['file_names'] ## should be MOCO_ch1.h5 and MOCO_ch2.h5
    save_path = args['save_path']
    # smooth = args['smooth']
    # colors = args['colors']
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
    moco_ch1 = os.path.join(save_path, 'MOCO_ch1.h5')
    moco_ch2 = os.path.join(save_path, 'MOCO_ch2.h5')    
    
    save_file_ch1_z = os.path.join(save_path, 'zscore_ch1.h5')
    save_file_ch2_z = os.path.join(save_path, 'zscore_ch2.h5')

    
