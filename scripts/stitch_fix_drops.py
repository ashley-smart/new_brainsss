"""will stitch together the fragmented nii files and add empty timepoint to account for bad indexing in creating split nii.
empty timepoint will appear at the end of each stiched file"""


import time
import sys
import os
import re
import json
import datetime
import textwrap
import numpy as np
import nibabel as nib
import gc



#get to files
#date = '20211215'
dates = ['20230714']  #as of 4-27 4-5 still has one bad fly as does 330
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
    #full_brain_ch1 = []
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
    # if len(channel_1_list) >= 10:
    #    print("ERROR: There are too many nii files to sort")
    #    break

    #new way of splitting causes problems for sort. need to find the number must have format 's###.nii' and will find ###
    values = []
    for nii in channel_1_list:
       start = nii.rindex('s') + 1 #+1 to get indexing right (want to start with number) (rindex gives index of last occurance)
       end = nii.find('.') #should end just before file extension
       values.append(int(nii[start:end]))
    values_sorted = sorted(values)

    sorted_channel_1_list = []
    sorted_channel_2_list = []
    for number in values_sorted:
       sorted_channel_1_list.extend([file for file in channel_1_list if 's' + str(number) + '.nii' in file])
       sorted_channel_2_list.extend([file for file in channel_2_list if 's' + str(number) + '.nii' in file])
    sorted_channel_1_list = sorted_channel_1_list
    sorted_channel_2_list = sorted_channel_2_list
    print('sorted_channel_1_list', sorted_channel_1_list)
    print('sorted_channel_2_list', sorted_channel_2_list)

    #iterate through sorted list and append files
    for i in range(len(sorted_channel_1_list)): 
        partial_brain_file = sorted_channel_1_list[i] #need the [0] because previous list comprehension
        print('current ch1 partial file: ', partial_brain_file)
        brain_ch1 = np.asarray(nib.load(os.path.join(directory, partial_brain_file)).get_data(), dtype='uint16')
        print('shape of partial brain file = ', np.shape(brain_ch1))
        if i > 0:
            full_brain_ch1 = np.append(full_brain_ch1, brain_ch1, axis = 3)
        elif i == 0:
            full_brain_ch1 = brain_ch1
        ## add the empty timepoint should be shape x,y,z,1 and full of nans or zeros. need to decide which is better
        ##I think it should be
        shape = np.shape(brain_ch1)
        blank_timepoint = np.empty((shape[0], shape[1], shape[2], 1)) * np.nan  #if want zeros then just get rid of nan part or use np.zeros(shape[0], shape[1], shape[2], 1)
        print(f'blank timepoint shape = {np.shape(blank_timepoint)}')
        full_brain_ch1 = np.append(full_brain_ch1, blank_timepoint, axis = 3)
        print(f'current full brain shape = {np.shape(full_brain_ch1)}')

    #save files        
    if len(full_brain_ch1) > 0:       
#         stitched_brain_ch1 = np.concatenate(full_brain_ch1, axis = -1)  ##why am I doing this?? I think from prev list append
#         print(f'concatenated ch1 shape = {np.shape(stitched_brain_ch1)}')
        #save stiched brain
        save_file = os.path.join(directory, 'ch1_stitched_fix.nii')  #it is important this is saved as ch1 rather than channel so it doesn't try to get restitched if the code runs twice
        aff = np.eye(4)
        img = nib.Nifti1Image(full_brain_ch1, aff)
        img.to_filename(save_file)
        del full_brain_ch1  #to delete from memory
#         del stitched_brain_ch1 # to delete from memory
        del img
        gc.collect()  #extra delete from memory
        time.sleep(30)  ##to give to time to delete

    print('CH1 COMPLETE for: ', str(directory))

    # now running ch2
    ### splitting this up to help the memory (hopefully)

    

    #iterate through sorted list and append files
    for i in range(len(sorted_channel_2_list)): 
        partial_brain_file = sorted_channel_2_list[i] #need the [0] because previous list comprehension
        print('current ch2 partial file: ', partial_brain_file)
        brain_ch2 = np.asarray(nib.load(os.path.join(directory, partial_brain_file)).get_data(), dtype='uint16')
        print('shape of partial brain file = ', np.shape(brain_ch2))
        if i > 0:
            full_brain_ch2 = np.append(full_brain_ch2, brain_ch2, axis = 3)
        elif i == 0:
            full_brain_ch2 = brain_ch2
        ## add the empty timepoint should be shape x,y,z,1 and full of nans or zeros. need to decide which is better
        ##I think it should be
        shape = np.shape(brain_ch2)
        blank_timepoint = np.empty((shape[0], shape[1], shape[2], 1)) * np.nan  #if want zeros then just get rid of nan part or use np.zeros(shape[0], shape[1], shape[2], 1)
        print(f'blank timepoint shape = {np.shape(blank_timepoint)}')
        full_brain_ch2 = np.append(full_brain_ch2, blank_timepoint, axis = 3)
        print(f'current full brain shape = {np.shape(full_brain_ch2)}')

    if len(full_brain_ch2) > 0:
        #         stitched_brain_ch1 = np.concatenate(full_brain_ch2, axis = -1)  ##why am I doing this?? I think from prev list append
#         print(f'concatenated ch1 shape = {np.shape(stitched_brain_ch2)}')
        #save stiched brain
        save_file = os.path.join(directory, 'ch2_stitched_fix.nii')  #it is important this is saved as ch1 rather than channel so it doesn't try to get restitched if the code runs twice
        aff = np.eye(4)
        img = nib.Nifti1Image(full_brain_ch2, aff)
        img.to_filename(save_file)
        del full_brain_ch2  #to delete from memory
#         del stitched_brain_ch2 # to delete from memory
        del img
        gc.collect()  #extra delete from memory
        time.sleep(30)  ##to give to time to delete
    print('CH2 COMPLETE for: ', str(directory))
