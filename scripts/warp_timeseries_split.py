import numpy as np
import os
import sys
import psutil
import nibabel as nib
from time import time
import json
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append("/home/users/asmart/projects/new_brainsss/")
os.listdir("/home/users/asmart/projects/new_brainsss/")
sys.path.append("/home/users/asmart/projects/new_brainsss/brainsss")
import brainsss
import matplotlib.pyplot as plt
from contextlib import contextmanager
import warnings
warnings.filterwarnings("ignore")
from shutil import copyfile
import ants
import h5py

def main(args):

    logfile = args['logfile']
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    fly_directory = args['directory']
    moving_path = args['moving_path']
    save_directory = args['save_directory']
    anat_file = args['anat_file']
    
    printlog(f'args: {args}')
    save_directory = os.path.join(fly_directory, 'warp')
    save_directory = os.path.join(fly_directory, 'warp')
    
    #my moving path should be MOCO_ch2_highpass_full_zscore_rem_light.h5
    ## Bella's moving_path 
    # moving_path = os.path.join(fly_directory, 'func_0', 'functional_channel_2_moco_zscore_highpass.h5')

    ###################
    ### Load Brains ###
    ###################
    fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/FDA_at_func_res_PtoA.nii"
    fixed = np.asarray(nib.load(fixed_path).get_data().squeeze(), dtype='float32')
    fixed = ants.from_numpy(fixed)
    fixed.set_spacing((2.611,2.611,5))

    with h5py.File(moving_path, 'r') as hf:
        #moving = hf['data'][:]
        moving = hf['zscore'][:]
    moving = ants.from_numpy(moving)
    moving.set_spacing((2.611, 2.611, 5, 1))
    dims = np.shape(moving)
    printlog(f' brain dims = {dims}')

    ###########################
    ### Organize Transforms ###
    ###########################
    #moving_fly.split('/')[-1] + '-to-' + fixed_fly.split('/')[-1]
    #save_directory, '{}-to-{}_invtransforms'.format(moving_fly.split('/')[-1], fixed_fly.split('/')[-1])
    fly_name = fly_directory.split('/')[-1]
    original_warp_path = os.path.join(fly_directory, 'warp')
    func_to_anat_affine_folder = '{}-to-{}_fwdtransforms_2umiso'.format(fly_name, anat_file)
    
    #I don't like how this doesn't filter for type => redoing like below
    #affine_file = os.listdir(os.path.join(original_warp_path, inv_warp_dir))[0]  ## why is this 0 indexed? oh to get the fist one... 
    #affine_path = os.path.join(save_directory, 'func-to-anat_fwdtransforms', affine_file)
    affine_files = os.listdir(os.path.join(original_warp_path, func_to_anat_affine_folder))
    #decided that affine should be .mat
    affine_path = os.path.join(original_warp_path, func_to_anat_affine_folder, [x for x in affine_files if '.mat' in x][0])


    ###need to do the same thing here!!! 
    #warp_dir = 'anat-to-FDA076iso_fwdtransforms'  ##what script makes this file? maybe its anat to meanbrain?
    ##not confident this is the same as above
    warp_dir = 'anat-to-meanbrain_fwdtransforms_2umiso'
    syn_files = os.listdir(os.path.join(original_warp_path, warp_dir))
    #syn_files = os.listdir(os.path.join(save_directory, warp_dir))
    syn_linear_path = os.path.join(original_warp_path, warp_dir, [x for x in syn_files if '.mat' in x][0])
    syn_nonlinear_path = os.path.join(original_warp_path, warp_dir, [x for x in syn_files if '.nii.gz' in x][0])

    transforms = [syn_nonlinear_path, syn_linear_path, affine_path]
    printlog(f'syn_nonlinear: {syn_nonlinear_path}')
    printlog(f'syn_linear: {syn_linear_path}')
    printlog(f'affine: {affine_path}')

    ########################
    ### Apply Transforms ###
    ########################
    printlog("applying transforms....")
    #warp to first half of brain
    half_timestamps = (dims[-1]/2)
    printlog(f'first half of brain ends at half_timestamps')
    warped_1 = ants.apply_transforms(fixed, moving[:,:,:,:half_timestamps], transforms, imagetype=3, interpolator='nearestNeighbor')
    #save_file = os.path.join(fly_directory, 'func_0', 'brain_in_FDA.nii')
    save_file_1 = os.path.join(save_directory, 'brain_in_FDA_1.nii') #first half
    nib.Nifti1Image(warped_1.numpy(), np.eye(4)).to_filename(save_file_1)
    printlog('saved first half')
    ##second half
    warped_2 = ants.apply_transforms(fixed, moving[:,:,:,half_timestamps:], transforms, imagetype=3, interpolator='nearestNeighbor')
    save_file_2 = os.path.join(save_directory, 'brain_in_FDA_2.nii') #second half
    nib.Nifti1Image(warped_2.numpy(), np.eye(4)).to_filename(save_file_2)
    printlog('saved second half')


    full_brain_warped = np.concatenate([warped_1, warped_2], axis = dims[-1])
    save_file_full = os.path.join(save_directory, 'brain_in_FDA.nii') #full
    nib.Nifti1Image(full_brain_warped.numpy(), np.eye(4)).to_filename(save_file_full)
    printlog('saved full brain')
    
    
    
    
    


def sec_to_hms(t):
        secs=F"{np.floor(t%60):02.0f}"
        mins=F"{np.floor((t/60)%60):02.0f}"
        hrs=F"{np.floor((t/3600)%60):02.0f}"
        return ':'.join([hrs, mins, secs])

@contextmanager
def stderr_redirected(to=os.devnull):

    fd = sys.stderr.fileno()

    def _redirect_stderr(to):
        sys.stderr.close() # + implicit flush()
        os.dup2(to.fileno(), fd) # fd writes to 'to' file
        sys.stderr = os.fdopen(fd, 'w') # Python writes to fd

    with os.fdopen(os.dup(fd), 'w') as old_stderr:
        with open(to, 'w') as file:
            _redirect_stderr(to=file)
        try:
            yield # allow code to be run with the redirected stdout
        finally:
            _redirect_stderr(to=old_stderr) # restore stdout.
                                            # buffering and flags such as
                                            # CLOEXEC may be different

if __name__ == '__main__':
    main(json.loads(sys.argv[1]))