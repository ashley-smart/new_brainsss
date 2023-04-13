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
        save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_zscore.h5')
        with h5py.File(full_load_path, 'r') as hf:   #if want to add zscore to theis file as a new key need to change to 'a' to read+write
            printlog("opened moco 2 file")
            ##data = hf['data']  #this syntax shouldn't load the whole thing in memory  ##THIS NEEDS TO CHANGE TO HIGH PASS FILTER 
            data = hf['high pass filter data']
            #get the dimension of the data
            dims = np.shape(data)
            
            steps = list(range(0,dims[-1],stepsize))
            steps.append(dims[-1])  #why is time appended? maybe I shouldn't do chunks on time below?
            
            #make file to save zscore data to 
            ##make new file so if it does somethign weird it doesn't corrupt the high pass data
            with h5py.File(save_file, 'w') as f:
                # check if zscore key already exists
                if 'zscore' in hf.keys():
                    print('zscore key-dataset already exists--overwriting')
                    # Note: I may want to change this later so it doesn't redo the zscore calculations
                    del hf['zscore']
                    dset = f.create_dataset('zscore', dims, dtype='float32', chunks=True)  
                else:
                    #zscore = hf.create_dataset('zscore', (*dims[:3],0), maxshape=(*dims[:3],None), dtype='float32')
                    dset = f.create_dataset('zscore', dims, dtype='float32', chunks=True)
                    print('created zscore key')

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
                                    
                    f['zscore'][:,:,chunk_start:chunk_end,:] = each_zscore
                                    

            printlog('ZSCORE complete')
        

    
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
