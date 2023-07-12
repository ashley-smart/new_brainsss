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
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
    stepsize = 25 ##this is set so memory doesn't get overwhelmed. lower if getting oom errors
    exp_types = ['20', '40', 'dark'] #must be this format ['20', '40', dark] #skip dark if don't want it


    for brain_file in file_names:
        full_load_path = os.path.join(directory, brain_file)
        save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_switch_zscore.h5')
        with h5py.File(full_load_path, 'r') as hf:   #if want to add zscore to theis file as a new key need to change to 'a' to read+write
            print(f"opened {brain_file}")
            data = hf['high pass filter data']
            #get the dimension of the data
            dims = np.shape(data)
            print('data acquired')
                     
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
                        print(f'{zscore_key}-dataset already exists--overwriting')
                        if overwrite == True:
                            del hf[zscore_key]
                            dset = f.create_dataset(zscore_key, dims, dtype='float32', chunks=True)  
                        elif overwrite == False:
                            print(f'ZSCORE {zscore_key}already exists and no overwrite selected => ending {brain_file}')            
                            break
                    else:
                        #the dims will be smaller than the actual zscore data...is that ok?
                        dset = f.create_dataset(zscore_key, dims, dtype='float32', chunks=True)
                        print(f'created {zscore_key} key')


                    #find switch set
                    if exp != 'dark' and int(exp) == exp_length1:
                        print(f'first experiment {exp}')
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
                            print('starting new switch set')
                            start = switch[0]
                            end = switch[1] #because set up as pairs in an array to be start and end
                            steps = list(range(start, end, stepsize))
                            steps.append(end) #to amke sure it goes to the end inclusively
                            number_timepoints = end - start
                            total_timepoints += number_timepoints
                            print(f'steps {steps}')

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
                                print(f'{np.shape(each_zscore)} is the {exp} expt zscore shape for chunk # {chunk_num}')
                                #printlog(f'{np.shape(each_zscore)} is the 20 expt zscore shape for chunk # {chunk_num}')
                                f[zscore_key][:,:,:, chunk_start:chunk_end] = each_zscore
                    
                    elif switch_set_t == None and exp == 'dark':
                        dark_total_timepoints = 0
                        dark_meanbrain = 0
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
                        print('dark steps', dark_steps)
                        print(len(dark_steps))

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
                            print(f'{np.shape(each_zscore)} is the {exp} expt zscore shape for chunk # {chunk_num}')
                            #printlog(f'{np.shape(each_zscore)} is the 20 expt zscore shape for chunk # {chunk_num}')
                            f['dark zscore'][:,:,:, chunk_start:chunk_end] = each_zscore

            print(f'ZSCORE complete for {brain_file}')
        

    
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))

