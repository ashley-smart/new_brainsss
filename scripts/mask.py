##from bella 3.14.24 https://github.com/lukebrez/dataflow/blob/master/sherlock_scripts/mask.py

import os
import sys
import numpy as np
import argparse
import subprocess
import json
import time
import scipy
from scipy import ndimage
from scipy.ndimage import gaussian_filter1d
import h5py

import nibabel as nib
# import bigbadbrain as bbb
#import dataflow as flow

from skimage.filters import threshold_triangle as tri_thresh
from skimage.filters import threshold_yen as yen_thresh
from skimage.filters import threshold_isodata as iso_thresh
from skimage.filters import threshold_li as li_thresh

sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append("/home/users/asmart/projects/new_brainsss/")
os.listdir("/home/users/asmart/projects/new_brainsss/")
sys.path.append("/home/users/asmart/projects/new_brainsss/brainsss")
import brainsss

import functions as fun

def main(args):

    logfile = args['logfile']
    directory = args['directory'] # full fly func path
    #file = args['file']
    #printlog = getattr(flow.Printlog(logfile=logfile), 'print_to_log')
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    brain_id = 'MOCO_ch2_highpass_full_zscore_rem_light.h5' #brain to apply mask to
    mean_id = 'MOCO_ch_mean.nii' #mean to generate mask
    #mean_path = f"/oak/stanford/groups/trc/data/Ashley2/imports/{date}/{fly_name}/{mean_file}"


    #brain_file = os.path.join(directory, mean_id) ## this should be meanbrain
    printlog("masking {}".format(brain_file))
    
    ### Load Brain ###
    brain = np.array(nib.load(brain_file).get_data(), copy=True)

    ### Load brain to use as mask ###
    brain_file = os.path.join(directory, mean_id) ##mean brain
    brain_mean = np.array(nib.load(brain_file).get_data(), copy=True)

    ### Mask ###
    printlog('masking')

    # Custom auto-threshold finder; trained a linear model
    yen = yen_thresh(brain_mean,nbins=1000)
    tri = tri_thresh(brain_mean)
    iso = iso_thresh(brain_mean,nbins=1000)
    li = li_thresh(brain_mean)
    threshold = 0.00475597*tri + 0.01330587*yen + -0.04362137*iso + 0.1478071*li + 36.46
    brain_mean[np.where(brain_mean < threshold)] = 0

    # Erode to remove extra-brain regions
    brain_mean = ndimage.binary_erosion(brain_mean, structure=np.ones((5,5,1)))
    
    # Find blobs not contiguous with largest blob
    labels, label_nb = scipy.ndimage.label(brain_mean)
    brain_label = np.bincount(labels.flatten())[1:].argmax()+1
    mask = np.ones(brain_mean.shape)
    mask[np.where(labels != brain_label)] = 0 # np.nan here failed with PCA
    
    # Undo previous erosion
    mask = ndimage.binary_dilation(mask, structure=np.ones((5,5,1))).astype(int)

    # Mask edges with zeros
    mask[:,(0,1,-1,-2),:] = 0
    mask[(0,1,-1,-2),:,:] = 0
    mask[:,:,(0,-1)] = 0

    # save mask
    brain_save_file = os.path.join(directory, 'mask.nii')
    nib.Nifti1Image(mask, np.eye(4)).to_filename(brain_save_file)

    # apply mask (consider revising how this is saved to go faster)
    brain_path = os.path.join(directory, brain_id) ##brain to mask
    with h5py.File(brain_path, 'r') as hf:
        #printlog(hf.keys())
        brain = hf['zscore']
        brain = brain*mask[:,:,:,None]
        printlog('made masked brain')
        # Save masked brain 
        brain_save_file = os.path.join(directory, 'brain_zscore_hp_moco_rem_light_masked.nii') #<---------------------------------------
        brain_save_file_h5 = os.path.join(directory, 'brain_zscore_hp_moco_rem_light_masked.h5')
        #nib.Nifti1Image(brain, np.eye(4)).to_filename(brain_save_file)
        with h5py.File(brain_save_file_h5, 'w') as f:
            key = 'zscore'
            fun.add_to_h5(brain_save_file_h5, key, brain)
    # Save masked brain 
    # brain_save_file = os.path.join(directory, 'brain_zscored_red_high_pass_masked.nii') #<---------------------------------------
    # nib.Nifti1Image(brain, np.eye(4)).to_filename(brain_save_file)

if __name__ == '__main__':
    main(json.loads(sys.argv[1]))