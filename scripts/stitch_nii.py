import time
import sys
import os
import re
import json
import datetime
import pyfiglet
import textwrap



#get to files
date = '20210806'
dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
fly_folders = os.listdir(dataset_path)  ## find directory names, they are the fly names


for fly in fly_folders: 
  directory = os.path.join(dataset_path, fly)
  for file in files:
      ## stitch brain ##
      if "channel_1" in file:
          brain_ch1 = np.asarray(nib.load(os.path.join(directory, file)).get_data(), dtype='uint16')
          full_brain_ch1.append(brain_ch1)
      elif "channel_2" in file:
          brain_ch2 = np.asarray(nib.load(os.path.join(directory, file)).get_data(), dtype='uint16')
          full_brain_ch2.append(brain_ch2)
          
  #save files        
  if len(full_brain_ch1) > 0:       
      stitched_brain_ch1 = np.concatenate(full_brain_ch1, axis = -1)
      #save stiched brain
      save_file = os.path.join(directory, '_ch1_stitched.nii')
      aff = np.eye(4)
      img = nib.Nifti1Image(stitched_brain_ch1, aff)
      img.to_filename(save_file)
      printlog("ch1 brain stitched and saved")

  if len(full_brain_ch2) > 0:
      stitched_brain_ch2 = np.concatenate(full_brain_ch2, axis = -1)
      #save stitched brain
      save_file = os.path.join(directory, '_ch2_stitched.nii')
      aff = np.eye(4)
      img = nib.Nifti1Image(stitched_brain_ch2, aff)
      img.to_filename(save_file)
      printlog("ch2 brain stiched and saved")
