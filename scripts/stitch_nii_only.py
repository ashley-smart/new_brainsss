import time
import sys
import os
import re
import json
import datetime
import pyfiglet
import textwrap
import numpy as np
import nibabel as nib
import gc



#get to files
#date = '20211215'
dates = ['20230131'] 
for date in dates:
  print('STARTING DATE:', str(date))
  dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
  #dataset_path = "/oak/stanford/groups/trc/data/krave/bruker_data/imports/" + str(date)
  
  fly_files = os.listdir(dataset_path)  ## find directory names, they are the fly names
  fly_folders = []
  for i in fly_files:
    if os.path.isdir(os.path.join(dataset_path, i)):
      fly_folders.append(i)
  print('found flies: ', len(fly_folders))


  for fly in fly_folders: 
    directory = os.path.join(dataset_path, fly)
    files = os.listdir(directory)
    full_brain_ch1 = []
    full_brain_ch2 = []
    channel_1_list = []
    channel_2_list = []
    for file in files:
        ## stitch brain ##
        #append all appropriate nii files together
        # these need to be appended in order so first make a list of ch specific files then sort later

        if "channel_1" in file and "nii" in file: 
            channel_1_list.append(file)
        elif "channel_2" in file and "nii" in file:
            channel_2_list.append(file)

    #then sort the files Note: this will fail if there are more than 10 items
#     print('channel_1_list', channel_1_list)
#     print('channel_2_list', channel_2_list)

    sorted_channel_1_list = sorted(channel_1_list)  
    sorted_channel_2_list = sorted(channel_2_list)
    print('sorted_channel_1_list', sorted_channel_1_list)
    print('sorted_channel_2_list', sorted_channel_2_list)

    #iterate through sorted list and append files
    for i in sorted_channel_1_list: 
        #print('ch1 file: ', i)
        brain_ch1 = np.asarray(nib.load(os.path.join(directory, i)).get_data(), dtype='uint16')
        #print('shape of brain file: ', np.shape(brain_ch1))
        full_brain_ch1.append(brain_ch1)


    #save files        
    if len(full_brain_ch1) > 0:       
        stitched_brain_ch1 = np.concatenate(full_brain_ch1, axis = -1)
        print('concatenated ch1')
        #save stiched brain
        save_file = os.path.join(directory, 'ch1_stitched.nii')  #it is important this is saved as ch1 rather than channel so it doesn't try to get restitched if the code runs twice
        aff = np.eye(4)
        img = nib.Nifti1Image(stitched_brain_ch1, aff)
        img.to_filename(save_file)
        del full_brain_ch1  #to delete from memory
        del stitched_brain_ch1 # to delete from memory
        gc.collect()  #extra delete from memory
    print('CH1 COMPLETE for: ', str(directory))

    # now running ch2
    ### splitting this up to help the memory (hopefully)

    #iterate through sorted list and append files
    for i in sorted_channel_2_list: 
        #print('ch2 file: ', i)
        brain_ch2 = np.asarray(nib.load(os.path.join(directory, i)).get_data(), dtype='uint16')
        #print('shape of brain file: ', np.shape(brain_ch2))
        full_brain_ch2.append(brain_ch2)

    if len(full_brain_ch2) > 0:
        stitched_brain_ch2 = np.concatenate(full_brain_ch2, axis = -1)
        print('concatenated ch2')

        #save stitched brain
        save_file = os.path.join(directory, 'ch2_stitched.nii')
        aff = np.eye(4)
        img = nib.Nifti1Image(stitched_brain_ch2, aff)
        img.to_filename(save_file)
        del full_brain_ch2  #to delete from memory
        del stitched_brain_ch2 # to delete from memory
        gc.collect()
    print('CH2 COMPLETE for: ', str(directory))
