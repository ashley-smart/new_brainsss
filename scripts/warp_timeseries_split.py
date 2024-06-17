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
import gc

def main(args):
    process = psutil.Process()
    logfile = args['logfile']
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    fly_directory = args['directory']
    moving_path = args['moving_path']
    save_directory = args['save_directory']
    anat_file = args['anat_file']
    
    printlog(f'args: {args}')
    save_directory = os.path.join(fly_directory, 'warp')
    
    #my moving path should be MOCO_ch2_highpass_full_zscore_rem_light.h5
    ## Bella's moving_path 
    # moving_path = os.path.join(fly_directory, 'func_0', 'functional_channel_2_moco_zscore_highpass.h5')

    ###################
    ### Load Brains ###
    ###################
    #what Bella uses
    #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/FDA_at_func_res_PtoA.nii"
    #what I used for alignment
    #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"
    # new alignment 76 FDA
    fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_076iso.nii"

    fixed = np.asarray(nib.load(fixed_path).get_data().squeeze(), dtype='float32')
    fixed = ants.from_numpy(fixed)
    #fixed.set_spacing((2.611,2.611,5)) #should this change?
    fixed.set_spacing((0.76,0.76,5)) #guessing here...
    fixed_dims = np.shape(fixed)


    with h5py.File(moving_path, 'r') as hf:
        #moving = hf['data'][:]
        #moving = hf['zscore'][:]
        moving = hf['zscore']
        
        
        #moving = ants.from_numpy(moving)  #apply transforms wants this format
        #moving.set_spacing((2.611, 2.611, 5, 1)) #I set this later in split version
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
        
        #affine_file = os.listdir(os.path.join(original_warp_path, inv_warp_dir))[0]  ## 0 to get first file 
        #affine_path = os.path.join(save_directory, 'func-to-anat_fwdtransforms', affine_file)
        affine_files = os.listdir(os.path.join(original_warp_path, func_to_anat_affine_folder))
        #I believe that affine should be .mat
        affine_path = os.path.join(original_warp_path, func_to_anat_affine_folder, [x for x in affine_files if '.mat' in x][0])


        #warp_dir = 'anat-to-meanbrain_fwdtransforms_2umiso'
        warp_dir = 'anat-to-FDA076iso_fwdtransforms' #newer
        syn_files = os.listdir(os.path.join(original_warp_path, warp_dir))
        #syn_files = os.listdir(os.path.join(save_directory, warp_dir))
        syn_linear_path = os.path.join(original_warp_path, warp_dir, [x for x in syn_files if '.mat' in x][0])
        syn_nonlinear_path = os.path.join(original_warp_path, warp_dir, [x for x in syn_files if '.nii.gz' in x][0])

        transforms = [syn_nonlinear_path, syn_linear_path, affine_path]
        printlog(f'syn_nonlinear: {syn_nonlinear_path}')
        printlog(f'syn_linear: {syn_linear_path}')
        printlog(f'affine: {affine_path}')
        printlog(f'current memory{psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2}')

        ########################
        ### Apply Transforms ###
        ########################
        ## looping in an h5py so I don't get oom errors
        stepsize = 100 
        new_dims = np.append(fixed_dims, dims[-1])
        save_file = make_empty_h5(save_directory, "brain_in_FDA.h5", new_dims) 
        steps = list(range(0,dims[-1],stepsize))
        with h5py.File(save_file, 'a') as f:
            for step_index in range(len(steps)):
                current_step = steps[step_index]
                if current_step == steps[-1]: #condition for the last step
                    each_moving_segment = moving[:,:,:,current_step:] #to make sure I get all the data
                    each_moving_segment = ants.from_numpy(each_moving_segment)
                    each_moving_segment.set_spacing((2.611, 2.611, 5, 1))
                    warped_time_segment = ants.apply_transforms(fixed, each_moving_segment, transforms, imagetype=3, interpolator='nearestNeighbor')
                    f['data'][...,current_step:] = warped_time_segment.numpy()
                    printlog(f'stored last section dims = {np.shape(warped_time_segment)}')
                else:
                    next_step = steps[step_index + 1]
                    each_moving_segment = moving[:,:,:,current_step:next_step]
                    each_moving_segment = ants.from_numpy(each_moving_segment)
                    each_moving_segment.set_spacing((2.611, 2.611, 5, 1))
                    warped_time_segment = ants.apply_transforms(fixed, each_moving_segment, transforms, imagetype=3, interpolator='nearestNeighbor')
                    f['data'][...,current_step:next_step] = warped_time_segment.numpy()

                printlog(f'current memory: {psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2}')
                printlog(f'step index = {step_index}')
        printlog('completed')
        

    
    
        ## full brain at once version
        # printlog("applying transforms....")
        # moving = ants.from_numpy(moving)  #apply transforms wants this format
        # moving.set_spacing((2.611, 2.611, 5, 1))
        # warped = ants.apply_transforms(fixed, moving, transforms, imagetype=3, interpolator='nearestNeighbor')
        # save_file = os.path.join(save_directory, 'brain_in_FDA.nii')
        # nib.Nifti1Image(warped.numpy(), np.eye(4)).to_filename(save_file)


    
    
    
    
def make_empty_h5(directory, file, brain_dims):
        savefile = os.path.join(directory, file)
        with h5py.File(savefile, 'w') as f:
            dset = f.create_dataset('data', brain_dims, dtype='float32', chunks=True)
        return savefile   


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