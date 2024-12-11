##this calculates dff by experimental block
##also saves meanbran and std of blocks seperately

#these are my functions
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
import re


def main(args):
    
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']

    overwrite = False #to redo calculations
    roi_peaks = True
    
    # rem_light = True #to remove light flash times from the zscore data (will resave as new h5 file)
    # printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    # light_buffer = 200 #ms needed away from light peak to allow brain volume to not be marked as light
    # redo_rem_light = True # if true will redo remove light and readd it to peaks
    # redo_light_peaks = True
    
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')


    date_string = directory.split('/')[-2] #this could have __queue__ or something in it so scrape it for digits
    date = re.findall(r'\d+', date_string )[0]
    if date > '20231101':
        fix = False
    else:
        fix = True
    printlog(f'Fixing timestamps for dropped frames = {fix}')
    #fix = True ##should the timestamps be corrected due to split_nii data drop? If date is before Nov 2023 then it should be True

    stepsize = 25 ##this is set so memory doesn't get overwhelmed. lower if getting oom errors
    exp_types = ['20', '40','dark'] #must be this format ['20', '40', dark] #skip dark if don't want it

    # ts_directory = os.path.join(date_path, fly_name)
    # timestamps = fun.find_timestamps(ts_directory, fix = fix)

    for brain_file in file_names:
        full_load_path = os.path.join(directory, brain_file)
    save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_dff.h5')
    data_file = full_load_path
    #key = 'high pass filter data'
    key = 'data rem light'
    
    with h5py.File(data_file, 'r') as hf:   #if want to add zscore to this file as a new key need to change to 'a' to read+write (I don't want to do that in case files get corrupted)
        print(f"opened {brain_file}")
        print(hf.keys())
        data = hf[key]
        #get the dimension of the data
        dims = np.shape(data)
        print('data acquired')
                     
        exp_length1 = int(exp_types[0])
        exp_length2 = int(exp_types[1])
        exp1_switch_set_t, exp2_switch_set_t = fun.get_brain_t_switch_set(directory, exp_length1 = exp_length1, exp_length2 = exp_length2, roi_peaks = roi_peaks)

        #make new file so if it does somethign weird it doesn't corrupt the high pass data
        #make stdbrain and meanbrain for dark period
        with h5py.File(save_file, 'w') as f:
            for exp in exp_types:
 
                #find switch set
                if exp != 'dark' and int(exp) == exp_length1:
                    print(f'first experiment {exp}')
                    switch_set_t = exp1_switch_set_t
                elif exp != 'dark' and int(exp) == exp_length2:
                    switch_set_t = exp2_switch_set_t
                elif exp == 'dark': #this is a special case
                    switch_set_t = None

                print(f'shape of exp switch 1: {np.shape(exp1_switch_set_t)}')
                print(f'shape of exp switch 2: {np.shape(exp2_switch_set_t)}')


                if exp == 'dark':
                    print("looking at dark condition")
                    dark_total_timepoints = 0
                    meanbrain = 0
                    if exp1_switch_set_t[0][0] < exp2_switch_set_t[0][0]:
                        print('twenty is first switch set')
                        end = exp1_switch_set_t[0][0] - 1 # -1 to not do same timepoint twice
                    else:
                        end = exp2_switch_set_t[0][0] - 1 # -1 to not do same timepoint twice
                        print('forty is the first switch set')

                    start = 0
                    dark_steps = list(range(start, end, stepsize))
                    dark_steps.append(end) #to make sure it goes to the end of the set inclusively
                    number_timepoints = end - start
                    dark_total_timepoints += number_timepoints #to add each switch set
                    print(f'dark steps {dark_steps}')
                    print(f'number dark steps {len(dark_steps)}')

                    #make meanbrain
                    meanbrain_dark = fun.make_meanbrain(dark_steps, data)
                    #save meanbrain per block
                    meanbrain_key = str(exp) + ' meanbrain'
                    fun.add_to_h5(save_file, meanbrain_key, meanbrain_dark)
                    print('saved meanbrain dark')

                    ##make std per block
                    stdbrain = fun.make_stdbrain (meanbrain, dark_steps, data)
                    std_key = str(exp) + ' std' 
                    fun.add_to_h5(save_file, std_key, stdbrain)  ##I may need to speficy dims to save this. if so change function
                    print('saved stdbrain')


    ##calculate dff based on saved meanbrain and darkbreain
    with h5py.File(data_file, 'r') as hf:   #if want to add zscore to this file as a new key need to change to 'a' to read+write (I don't want to do that in case files get corrupted)
        print(f"opened {brain_file}")
        print(hf.keys())
        data = hf[key]
        #get the dimension of the data
        dims = np.shape(data)
        print(f'brain dims {dims}')
        
        ##open dark meanbrain
        with h5py.File(save_file, 'a') as f:
            print(f"opened {save_file}")
            print(f.keys())
            dark_meanbrain = f['dark meanbrain']
            dims_mean = np.shape(dark_meanbrain)
            print(f'dims for dark brain = {dims_mean}')
            
            
            #calculate df/f for each timestep...(I should probably chunk this like zscore)
            #make empty dataset
            if 'dff' in f.keys():
                print(f'dff-dataset already exists--overwriting')
                if overwrite == True:
                    del hf["dff"]
                    dset = f.create_dataset("dff", dims, dtype='float32', chunks=True)  
                elif overwrite == False:
                    print(f'dff key already exists and no overwrite selected => ending {brain_file}')            
                    #break
            else:
                #the dims will be smaller than the actual zscore data...is that ok?
                dset = f.create_dataset("dff", dims, dtype='float32', chunks=True)
                print(f'created dff key')
            
            
            #create steps to make chunks
            total_timepoints = 0
            steps = list(range(0, dims[3], stepsize))
            steps.append(end) #to amke sure it goes to the end inclusively
            number_timepoints = end - start
            total_timepoints += number_timepoints
            for chunk_num in range(len(steps) -1):
                chunk_start = steps[chunk_num]
                chunk_end = steps[chunk_num + 1]
                chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                dff = (chunk - dark_meanbrain)/dark_meanbrain
                print(f'check dims dff = {np.shape(dff)}, chunk = {np.shape(chunk)}. Should be the same')
                f['dff'][:,:,:, chunk_start:chunk_end] = dff
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))

