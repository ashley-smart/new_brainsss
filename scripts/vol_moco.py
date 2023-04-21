 
## this will run moco on each volume independently and save to help with memory issues
## with Luke


import os
import sys
import numpy as np
import argparse
import subprocess
import json
from time import time
import nibabel as nib
import h5py
import ants
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
import brainsss



def main(args):

  logfile = args['logfile']
  directory = args['directory'] # full fly path 
  file_names = args['file_names'] ## should be ch2_stitched.nii and ch1_stitched.nii
  save_path = args['save_path']
  # smooth = args['smooth']
  # colors = args['colors']
  printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
  rerun_moco = False #will rerun moco even if it exists. Change to true if somethign wrong with moco 

  #save_file_ch1 = os.path.join(save_path, 'MOCO_ch1.h5')
  #save_file_ch2 = os.path.join(save_path, 'MOCO_ch2.h5')

  ########################################3
  ## see if already moco file
  if rerun_moco == False:
    for name in file_names:
      if 'MOCO' in name:
          printlog(f'MOCO FILE ALREADY EXISTS {name} => aborting')
          return
  
  # Get brain shape
  ch1_brain_file = None
  ch2_brain_file = None
  for name in file_names:
    if 'ch1' in name:
        ch1_brain_file = os.path.join(directory, name)
    elif 'ch2' in name:
        ch2_brain_file = os.path.join(directory, name)
    else:
        printlog("Aborting moco - could not find ch1 or ch2")
        return
                   
  if ch1_brain_file is None:
      printlog("Aborting moco - could not find ch1")
      return
        
  
  ### get brain dims
  ch1_img = nib.load(ch1_brain_file) # this loads a proxy
  ch1_shape = ch1_img.header.get_data_shape()
  brain_dims = ch1_shape
  printlog("Channel 1 shape is {}".format(brain_dims))

  #################################################################        
  #calculate the meanbrain of channel 1, which will be fixed in moco
  #############################################################
  printlog('meanbrain START...')
  t0 = time()
  meanbrain = np.zeros(brain_dims[:3])
  for i in range(brain_dims[-1]):
      meanbrain += ch1_img.dataobj[...,i]    
  meanbrain = meanbrain/brain_dims[-1] # divide by number of volumes
  fixed = ants.from_numpy(np.asarray(meanbrain, dtype='float32'))
  printlog('meanbrain DONE Duration: {}'.format(time()-t0))

  ### Load channel 2 proxy here ###
  if ch2_brain_file is not None:
      img_ch2 = nib.load(ch2_brain_file) # this loads a proxy
      # make sure channel 1 and 2 have same shape
      ch2_shape = img_ch2.header.get_data_shape()
      if ch1_shape != ch2_shape:
          printlog("Channel 1 and 2 do not have the same shape! {} and {}".format(ch1_shape, ch2_shape))
  #####################################################################         
  # Make empty hdf5 file to append processed volumes to with matching shape
  ######################################################################
#   with h5py.File(save_file_ch1, 'w') as f_ch1:
#       dset_ch1 = f_ch1.create_dataset('data', (*brain_dims[:3],0), maxshape=(*brain_dims[:3],None), dtype='float32')
#   printlog('created empty hdf5 file ch1')

#   if ch2_brain_file is not None: 
#       with h5py.File(save_file_ch2, 'w') as f_ch2:
#           dset_ch2 = f_ch2.create_dataset('data', (*brain_dims[:3],0), maxshape=(*brain_dims[:3],None), dtype='float32')
#       printlog('created empty hdf5 file ch2')
  
  save_file_ch1 = make_empty_h5(directory, "MOCO_ch1.h5", brain_dims)
  printlog('created empty hdf5 file  #: {}'.format("MOCO_ch1.h5"))

  if ch2_brain_file is not None:
      save_file_ch2 = make_empty_h5(directory, "MOCO_ch2.h5", brain_dims)
      printlog('created empty hdf5 file #: {}'.format("MOCO_ch2.h5"))
           
           
  ####################################################################3
  ## Start MOCO!!  ######
  # loop over all brain vols, motion correcting each and append to growing hdf5 file on disk
  printlog('moco vol by vol')
           
  ### prepare chunks to loop over ###
  # the stepsize defines how many vols to moco before saving them to h5 (this save is slow, so we want to do it less often)
  stepsize = 100 # if this is too high if may crash from memory error. If too low it will be slow.
  steps = list(range(0,brain_dims[-1],stepsize))
  # add the last few volumes that are not divisible by stepsize
  if brain_dims[-1] > steps[-1]:
      steps.append(brain_dims[-1])
           
  #for i in range(brain_dims[-1]):
  for j in range(len(steps)-1):
    #printlog(F"j: {j}")
           
    ### LOAD A SINGLE BRAIN VOL ###
    moco_ch1_chunk = []
    moco_ch2_chunk = []
    for i in range(stepsize):
      t0 = time()
      index = steps[j] + i
      # for the very last j, adding the step size will go over the dim, so need to stop here
      if index == brain_dims[-1]:
          break
           
      # Load a single brain volume
      vol = ch1_img.dataobj[...,index]

      ### Process vol (moco, zscore, etc) ###
      # Make ants image of ch1 brain
      moving = ants.from_numpy(np.asarray(vol, dtype='float32'))

      # Motion correct
      moco = ants.registration(fixed, moving, type_of_transform='SyN')
      moco_ch1 = moco['warpedmovout'].numpy()
      moco_ch1_chunk.append(moco_ch1)
      transformlist = moco['fwdtransforms']

      ##apply transforms to ch2 to make ch2 warped brain correction
      if ch2_brain_file is not None: 
        ch2_img = nib.load(ch2_brain_file) # this loads a proxy
        ch2_vol = ch2_img.dataobj[...,index]
        ch2_moving = ants.from_numpy(np.asarray(ch2_vol, dtype='float32'))
        moco_ch2 = ants.apply_transforms(fixed, ch2_moving, transformlist)
        moco_ch2 = moco_ch2.numpy()
        moco_ch2_chunk.append(moco_ch2)
        #printlog(F'moco vol done: {index}, time: {time()-t0}')


      ### DELETE INVERSE TRANSFORMS
      transformlist = moco['invtransforms']
      for x in transformlist:
        if '.mat' not in x:
         os.remove(x)

      ### DELETE FORWARD TRANSFORMS
      transformlist = moco['fwdtransforms']
      for x in transformlist:
        if '.mat' not in x:
         os.remove(x)

    moco_ch1_chunk = np.moveaxis(np.asarray(moco_ch1_chunk),0,-1)
    if ch2_brain_file is not None:
      moco_ch2_chunk = np.moveaxis(np.asarray(moco_ch2_chunk),0,-1)
           
    #################################     
    # Append to hdf5 file
    t0 = time()
    ## ch1 
    with h5py.File(save_file_ch1, 'a') as f_ch1:
      f_ch1['data'][...,steps[j]:steps[j+1]] = moco_ch1_chunk                                   
    #printlog(F'Ch_1 append time: {time()-t0}')
      
          ## ch2
    t0 = time()
    if ch2_brain_file is not None:
      with h5py.File(save_file_ch2, 'a') as f_ch2:
        f_ch2['data'][...,steps[j]:steps[j+1]] = moco_ch2_chunk
      #printlog(F'Ch_2 append time: {time()-t0}')
      
  printlog("DONE with moco")
           
def make_empty_h5(directory, file, brain_dims):
  savefile = os.path.join(directory, file)
  with h5py.File(savefile, 'w') as f:
    dset = f.create_dataset('data', brain_dims, dtype='float32', chunks=True)
  return savefile

## not currently used, but could be added in beginning
def check_for_file(file, directory):
  filepath = os.path.join(directory, file)
  if os.path.exists(filepath):
    return filepath
  else:
    return None
           
           
           
#           # Increase hdf5 size by one brain volume
#           current_num_vol = f_ch1['data'].shape[-1] # this is the last axis, which is time
#           new_num_vol = current_num_vol + 1 # will want one more volume
#           f_ch1['data'].resize(new_num_vol,axis=3) # increase size by one volume

#           # Append to hdf5 file
#           f_ch1['data'][...,-1] = moco_out  ##

#       printlog(F'vol ch1: {i}, time: {time()-t0}')

#       # Append to hdf5 file for ch2   ##Alternatively I could put them in the same file with different keys
#       if ch2_brain_file is not None:
#         with h5py.File(save_file_ch2, 'a') as f_ch2:

#             # Increase hdf5 size by one brain volume
#             current_num_vol = f_ch2['data'].shape[-1] # this is the last axis, which is time
#             new_num_vol = current_num_vol + 1 # will want one more volume
#             f_ch2['data'].resize(new_num_vol,axis=3) # increase size by one volume

#             # Append to hdf5 file
#             f_ch2['data'][...,-1] = moco_ch2
#         printlog(F'vol ch2: {i}, time: {time()-t0}')
#   printlog(F'MOCO DONE! Number of volumes completed: {i}')

           
if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
