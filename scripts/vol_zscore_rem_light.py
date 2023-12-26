## take moco h5py file and run zscore on it and add to h5py file in a new dataset/key
##currently adding the zscore data to the appropriate h5 file as a key called 'zscore'
## this is currently set to run each volume independently

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
import functions as fun

def main(args):
    
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']

    
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
    #brain_id = directory.split('/')[-1]
#     brain_file = 'MOCO_ch2.h5'
#     files =  brain_file.split('.')[0] + '_highpass.h5'
    
    stepsize = 25
    rem_light = True
    redo_light_peaks = True
    redo_rem_light = True
    fix = True
    light_buffer = 100
    
    
    #save_file = os.path.join(save_path, 'ch2_zscore_hp.h5')
    
    
#   #running on ch1 is a good idea to compare the red to green
#     ch1_filepath = None
#     ch2_filepath = None
    
#     files = []
#     for name in file_names:
#       if 'ch1' in name:
#         ch1_filepath = os.path.join(directory, name)
#         printlog(ch1_filepath) 
#         files.append(ch1_filepath)
#       elif 'ch2' in name:
#         ch2_filepath = os.path.join(directory, name)
#         printlog(ch2_filepath)
#         files.append(ch2_filepath)
#       else:
#         printlog('No file with ch1 or ch2 in it')
    
    
    for brain_file in file_names:
        full_load_path = os.path.join(directory, brain_file)
        #rerun timestamps, need to do this so if other functions call load timestamps it will pull the fixed version
        timestamps = fun.find_timestamps(directory, fix = fix)
        rem_light_file = os.path.join(save_directory, brain_file.split('.')[0] + '_data_rem_light.h5') #generate this file

        ##first replace light 
        if rem_light == True:
            with h5py.File(full_load_path, 'r') as hf:   #if want to add zscore to this file as a new key need to change to 'a' to read+write (I don't want to do that in case files get corrupted)
                printlog(f"opened {brain_file} for rem light")
                data = hf['high pass filter data']
                dims = np.shape(data)
                max_t = dims[-1]
                
                if redo_light_peaks == True:
                    ##this function calculates and resaves light peaks from voltage file rather than loading
                    #if want to redo must run this function first
                    ##otherwise the other functions will look for light peaks in the h5 file before generating it if it has been made before
                    light_peaks_ms = fun.get_light_peaks(directory)  

                
                    
                light_peaks_to_rem = fun.get_light_peaks_brain_time(directory, max_t, light_buffer)
                printlog(f'light peaks to rem: {light_peaks_to_rem}')
                fun.add_to_h5(rem_light_file, 'light peaks brain t', light_peaks_to_rem)
                printlog(f'added light peaks to h5')
                #new_data_file = fun.make_empty_h5(rem_light_file, 'data rem light', dims)
                #printlog('made empty dataset')
                with h5py.File(rem_light_file, 'a') as f:  
                    printlog('opened data file')
                    mask = np.zeros((1, 1, 1, dims[-1]), bool) # [1, 1, 1, dims[-1]]
                    mask[:, :, :, light_peaks_to_rem] = True
                    #if mask is true then replace withzeros otherwise replace with data
                    if 'data rem light' in f.keys() and redo_rem_light == False:
                        printlog('data rem light already in keys so skipping adding it')
                    elif 'data rem light' in f.keys() and redo_rem_light == True:
                        del f['data rem light']
                        f['data rem light'] = np.where(mask,
                                                    0,
                                                    data) 
                        printlog('prev mask removed, new mask made and stored in h5')
                    else:
                        f['data rem light'] = np.where(mask,
                                                    0,
                                                    data) 
                        printlog('mask made and stored in h5')
            data_file = rem_light_file
            key = 'data rem light'
            save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_full_zscore_rem_light.h5')
        else:
            data_file = full_load_path
            key = 'high pass filter data'
            save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_full_zscore.h5')
       
        #will use rem_light_file or full_load_path as data file depending on if rem_light is True or not
        with h5py.File(data_file, 'r') as hf:   #if want to add zscore to this file as a new key need to change to 'a' to read+write (I don't want to do that in case files get corrupted)
            printlog(f"opened {brain_file}")
            data = hf[key]
            #get the dimension of the data
            dims = np.shape(data)
            printlog('data acquired')
            
            steps = list(range(0,dims[-1],stepsize))
            steps.append(dims[-1])  #why is time appended? maybe I shouldn't do chunks on time below?
            
            #make file to save zscore data to 
            ##make new file so if it does somethign weird it doesn't corrupt the high pass data
            with h5py.File(save_file, 'w') as f:
                # check if zscore key already exists
                if 'zscore' in hf.keys():
                    printlog('zscore key-dataset already exists--overwriting')
                    # Note: I may want to change this later so it doesn't redo the zscore calculations
                    del hf['zscore']
                    dset = f.create_dataset('zscore', dims, dtype='float32', chunks=True)  
                else:
                    #zscore = hf.create_dataset('zscore', (*dims[:3],0), maxshape=(*dims[:3],None), dtype='float32')
                    dset = f.create_dataset('zscore', dims, dtype='float32', chunks=True)
                    printlog('created zscore key')

                #find meanbrain 
                meanbrain = 0
#                 for i in range(dims[-1]):  #dims[-1] gives number of timepoints => number of volumes
#                     meanbrain += data[:,:,:,i]   # replaces this with chunks just like in HighPass filtering. After high pass filtering, this should be okay to sum. Otherwise you would have needed the mean of means, which is safe
#                 meanbrain = meanbrain/dims[-1]
                
                for chunk_num in range(len(steps) - 1):  
                    chunk_start = steps[chunk_num]
                    chunk_end = steps[chunk_num + 1]
                    chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                    #below used to be just += chunk but I think summing over time is right since I'm dividing by # timepoints to get mean
                    meanbrain += np.sum(chunk, axis = 3, keepdims = True)   # replaces this with chunks just like in HighPass filtering. After high pass filtering, this should be okay to sum. Otherwise you would have needed the mean of means, which is safe
                    ##can I sum across chunk so I dont get summing error when it doesnt divide evenly? I think I can 
                meanbrain = meanbrain/dims[-1]  #this calculates the mean by dividing by total timepoints


                #find STD
                total = 0
                for chunk_num in range(len(steps) - 1):  
                    chunk_start = steps[chunk_num]
                    chunk_end = steps[chunk_num + 1]
                    chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                    s = np.sum((chunk - meanbrain)**2, axis = 3, keepdims = True) #changed to sum of chunk
                    total = s + total
                final_std = np.sqrt(total/dims[-1]) #fix this from len


                #calculate zscore
                for chunk_num in range(len(steps) - 1):  
                    chunk_start = steps[chunk_num]
                    chunk_end = steps[chunk_num + 1]
                    chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
                    each_zscore = (chunk - meanbrain)/final_std
                    #printlog(f'{np.shape(each_zscore)} is the zscore shape for chunk # {chunk_num}')
                    f['zscore'][:,:,:, chunk_start:chunk_end] = each_zscore
                                    

            printlog('ZSCORE complete')
        

    
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
