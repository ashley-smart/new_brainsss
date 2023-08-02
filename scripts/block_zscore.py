##this calculates zscore by experimental block
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


def main(args):
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']

    overwrite = True #to redo zscore data
    rem_light = True #to remove light flash times from the zscore data (will resave as new h5 file)
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    light_buffer = 100 #ms needed away from light peak to allow brain volume to not be marked as light
    
    stepsize = 25 ##this is set so memory doesn't get overwhelmed. lower if getting oom errors
    exp_types = ['20', '40','dark'] #must be this format ['20', '40', dark] #skip dark if don't want it


    for brain_file in file_names:
        full_load_path = os.path.join(directory, brain_file)
        rem_light_file = os.path.join(save_directory, brain_file.split('.')[0] + '_data_rem_light.h5')

        ##first replace light 
        if rem_light == True:
            with h5py.File(full_load_path, 'r') as hf:   #if want to add zscore to theis file as a new key need to change to 'a' to read+write
                printlog(f"opened {brain_file} for rem light")
                data = hf['high pass filter data']
                dims = np.shape(data)
                max_t = dims[-1]
                
                light_peaks_to_rem = fun.get_light_peaks_brain_time(directory, max_t, light_buffer)
                printlog(f'light peaks to rem: {light_peaks_to_rem}')
                fun.add_to_h5(rem_light_file, 'light peaks brain t', light_peaks_to_rem)
                printlog('added light peaks to h5')
                #new_data_file = fun.make_empty_h5(rem_light_file, 'data rem light', dims)
                #printlog('made empty dataset')
                with h5py.File(rem_light_file, 'a') as f:  
                    print('opened data file')
                    mask = np.zeros((1, 1, 1, dims[-1]), bool) # [1, 1, 1, dims[-1]]
                    mask[:, :, :, light_peaks_to_rem] = True
                    #if mask is true then replace withzeros otherwise replace with data
                    if 'data rem light' in f.keys():
                        printlog('data rem light already in keys so skipping adding it')
                    else:
                        f['data rem light'] = np.where(mask,
                                                    0,
                                                    data) 
                        printlog('mask made and stored in h5')
            data_file = rem_light_file
            key = 'data rem light'
            save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_switch_zscore_rem_light.h5')
        else:
            data_file = full_load_path
            key = 'high pass filter data'
            save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_switch_zscore.h5')
       
       
        with h5py.File(data_file, 'r') as hf:   #if want to add zscore to theis file as a new key need to change to 'a' to read+write
            printlog(f"opened {brain_file}")
            data = hf[key]
            #get the dimension of the data
            dims = np.shape(data)
            printlog('data acquired')
                     
            exp_length1 = int(exp_types[0])
            exp_length2 = int(exp_types[1])
            exp1_switch_set_t, exp2_switch_set_t = fun.get_brain_t_switch_set(directory, exp_length1 = exp_length1, exp_length2 = exp_length2)

            #make new file so if it does somethign weird it doesn't corrupt the high pass data
            with h5py.File(save_file, 'w') as f:
                for exp in exp_types:
                    #make zscore key

                    zscore_key = str(exp) + ' zscore'
                    ##make empty zscore dataset h5py
                    if zscore_key in f.keys():
                        printlog(f'{zscore_key}-dataset already exists--overwriting')
                        if overwrite == True:
                            del hf[zscore_key]
                            dset = f.create_dataset(zscore_key, dims, dtype='float32', chunks=True)  
                        elif overwrite == False:
                            printlog(f'ZSCORE {zscore_key}already exists and no overwrite selected => ending {brain_file}')            
                            break
                    else:
                        #the dims will be smaller than the actual zscore data...is that ok?
                        dset = f.create_dataset(zscore_key, dims, dtype='float32', chunks=True)
                        printlog(f'created {zscore_key} key')


                    #find switch set
                    if exp != 'dark' and int(exp) == exp_length1:
                        printlog(f'first experiment {exp}')
                        switch_set_t = exp1_switch_set_t
                    elif exp != 'dark' and int(exp) == exp_length2:
                        switch_set_t = exp2_switch_set_t
                    elif exp == 'dark': #this is a special case
                        switch_set_t = None

                    #find start and end points for each switch set

                    if switch_set_t is not None:
                        total_timepoints = 0 #this will count the number of timepoints for the all the blocks of the same exp type
                        for switch_i in range(len(switch_set_t)):
                            switch = switch_set_t[switch_i]
                            printlog('starting new switch set')
                            start = switch[0]
                            end = switch[1] #because set up as pairs in an array to be start and end
                            steps = list(range(start, end, stepsize))
                            steps.append(end) #to amke sure it goes to the end inclusively
                            number_timepoints = end - start
                            total_timepoints += number_timepoints
                            printlog(f'steps {steps}')

                            #make meanbrain per block
                            meanbrain = fun.make_meanbrain(steps, data)
                            #save meanbrain per block
                            meanbrain_block_key = str(exp) + ' meanbrain ' + str(switch_i)
                            fun.add_to_h5(save_file, meanbrain_block_key, meanbrain)
                            
                            ##make std per block
                            stdbrain = fun.make_stdbrain (meanbrain, steps, data)
                            std_block_key = str(exp) + ' std ' + str(switch_i)
                            fun.add_to_h5(save_file, std_block_key, stdbrain)  ##I may need to speficy dims to save this. if so change function

                            #calculate zscore
                            for chunk_num in range(len(steps) - 1):  
                                chunk_start = steps[chunk_num]
                                chunk_end = steps[chunk_num + 1]
                                chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                                each_zscore = (chunk - meanbrain)/stdbrain
                                printlog(f'{np.shape(each_zscore)} is the {exp} expt zscore shape for chunk # {chunk_num}')
                                #printlog(f'{np.shape(each_zscore)} is the 20 expt zscore shape for chunk # {chunk_num}')
                                f[zscore_key][:,:,:, chunk_start:chunk_end] = each_zscore
                    
                    elif switch_set_t == None and exp == 'dark':
                        dark_total_timepoints = 0
                        meanbrain = 0
                        if exp1_switch_set_t[0][0] < exp2_switch_set_t[0][0]:
                            printlog('twenty is first switch set')
                            end = exp1_switch_set_t[0][0] - 1 # -1 to not do same timepoint twice
                        else:
                            end = exp2_switch_set_t[0][0] - 1 # -1 to not do same timepoint twice
                            printlog('forty is the first switch set')

                        start = 0
                        dark_steps = list(range(start, end, stepsize))
                        dark_steps.append(end) #to make sure it goes to the end of the set inclusively
                        number_timepoints = end - start
                        dark_total_timepoints += number_timepoints #to add each switch set
                        printlog(f'dark steps {dark_steps}')
                        printlog(f'number dark steps {len(dark_steps)}')

                        #make meanbrain
                        meanbrain = fun.make_meanbrain(dark_steps, data)
                        #save meanbrain per block
                        meanbrain_key = str(exp) + ' meanbrain'
                        fun.add_to_h5(save_file, meanbrain_key, meanbrain)

                        ##make std per block
                        stdbrain = fun.make_stdbrain (meanbrain, dark_steps, data)
                        std_key = str(exp) + ' std' 
                        fun.add_to_h5(save_file, std_key, stdbrain)  ##I may need to speficy dims to save this. if so change function

                        #calculate zscore and save
                        for chunk_num in range(len(dark_steps) - 1):  
                            chunk_start = dark_steps[chunk_num]
                            chunk_end = dark_steps[chunk_num + 1]
                            chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                            each_zscore = (chunk - meanbrain)/stdbrain
                            printlog(f'{np.shape(each_zscore)} is the {exp} expt zscore shape for chunk # {chunk_num}')
                            #printlog(f'{np.shape(each_zscore)} is the 20 expt zscore shape for chunk # {chunk_num}')
                            f['dark zscore'][:,:,:, chunk_start:chunk_end] = each_zscore

            printlog(f'ZSCORE complete for {brain_file}')
        

    
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))

