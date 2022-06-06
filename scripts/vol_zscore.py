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
    file_names = args['file_names'] ## should be MOCO_ch1.h5 and MOCO_ch2.h5 as specified in vol_main.py
    save_path = args['save_path']
    # smooth = args['smooth']
    # colors = args['colors']
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
    
  
    ch1_filepath = None
    ch2_filepath = None
    files = []
    for name in file_names:
      if 'ch1' in name:
        ch1_filepath = os.path.join(directory, name)
        printlog(ch1_filepath) 
        files.append(ch1_filepath)
      elif 'ch2' in name:
        ch2_filepath = os.path.join(directory, name)
        printlog(ch2_filepath)
        files.append(ch2_filepath)
      else:
        printlog('No file with ch1 or ch2 in it')
    
    
    #open moco file for all files in files (should be ch1 and ch2
    for file in files:
        with h5py.File(file, 'a') as hf:   #if want to add zscore to theis file as a new key need to change to 'a' to read+write
            printlog("opened moco 2 file")
            data = hf['data']  #this syntax shouldn't load the whole thing in memory
            #get the dimension of the data
            dims = np.shape(data)

            #make file to save zscore data to 
            ##I had it make a new key in the existing file so I didn't have to mess with having multiple h5 files open at once
            # check if zscore dataset already created
            if 'zscore' in hf.keys():
                print('zscore key-dataset already exists')
            else:
                zscore = hf.create_dataset('zscore', (*dims[:3],0), maxshape=(*dims[:3],None), dtype='float32')
                print('created zscore key')


            #find meanbrain 
            meanbrain = 0
            for i in range(dims[-1]):  #dims[-1] gives number of timepoints => number of volumes
                meanbrain += data[:,:,:,i]
            meanbrain = meanbrain/dims[-1]

            #find std
            total = 0
            for i in range(dims[-1]):
                s = (data[:,:,:,i] - meanbrain)**2
                total = s + total
            final_std = np.sqrt(total/len(data[-1]))


            #calculate zscore
            for i in range(dims[-1]):
                each_zscore = (data[:,:,:,i] - meanbrain)/final_std

                #save zscore
                # Increase hdf5 size by one brain volume
                current_num_vol = hf['zscore'].shape[-1] # this is the last axis, which is time
                new_num_vol = current_num_vol + 1 # will want one more volume
                hf['zscore'].resize(new_num_vol,axis=3) # increase size by one volume

                # Append to hdf5 file
                hf['zscore'][...,-1] = each_zscore
                if i % 1000 == 0:  #to just report every 1000 volumes so file isn't so big
                    printlog(str(i) + " volume complete")
            printlog('ZSCORE complete')
        

    
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
