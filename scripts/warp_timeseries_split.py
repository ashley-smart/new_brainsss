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
    fixed.set_spacing((2.611,2.611,5)) #should this change?


    with h5py.File(moving_path, 'r') as hf:
        #moving = hf['data'][:]
        #moving = hf['zscore'][:]
        moving = hf['zscore']
        
        
        #moving = ants.from_numpy(moving)  #apply transforms wants this format
        #moving.set_spacing((2.611, 2.611, 5, 1))
        dims = np.shape(moving)
        printlog(f' brain dims = {dims}')

        ###########################
        ### Organize Transforms ###
        ###########################
        #moving_fly.split('/')[-1] + '-to-' + fixed_fly.split('/')[-1]
        #save_directory, '{}-to-{}_invtransforms'.format(moving_fly.split('/')[-1], fixed_fly.split('/')[-1])
        fly_name = fly_directory.split('/')[-1]
        original_warp_path = os.path.join(fly_directory, 'warp')
        
        #check this later. I think this is where it was saved
        func_to_anat_affine_folder = '{}-to-{}_fwdtransforms_2umiso'.format(fly_name, anat_file)
        
        
        #affine_file = os.listdir(os.path.join(original_warp_path, inv_warp_dir))[0]  ## 0 to get first file 
        #affine_path = os.path.join(save_directory, 'func-to-anat_fwdtransforms', affine_file)
        affine_files = os.listdir(os.path.join(original_warp_path, func_to_anat_affine_folder))
        #decided that affine should be .mat
        affine_path = os.path.join(original_warp_path, func_to_anat_affine_folder, [x for x in affine_files if '.mat' in x][0])


        
        #warp_dir = 'anat-to-FDA076iso_fwdtransforms'  
        ##not confident this is the same as above
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
        save_file = make_empty_h5(save_directory, "brain_in_FDA.h5", dims) 
        steps = list(range(0,dims[-1],stepsize))
        with h5py.File(save_file, 'a') as f:
            for step_index in range(len(steps)):
                current_step = steps[step_index]
                if current_step == steps[-1]: #condition for the last step
                    each_moving_segment = moving[:,:,:,current_step:] #to make sure I get all the data
                    each_moving_segment = ants.from_numpy(each_moving_segment)
                    each_moving_segment.set_spacing((2.611, 2.611, 5, 1))
                    warped_time_segment = ants.apply_transforms(fixed, each_moving_segment, transforms, imagetype=3, interpolator='nearestNeighbor')
                    f['data'][:,:,:,current_step:next_step] = warped_time_segment
                else:
                    next_step = steps[step_index + 1]
                    each_moving_segment = moving[:,:,:,current_step:next_step]
                    each_moving_segment = ants.from_numpy(each_moving_segment)
                    each_moving_segment.set_spacing((2.611, 2.611, 5, 1))
                    warped_time_segment = ants.apply_transforms(fixed, each_moving_segment, transforms, imagetype=3, interpolator='nearestNeighbor')
                    f['data'][:,:,:,current_step:next_step] = warped_time_segment
        
                printlog(f'current memory{psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2}')
                printlog(f'step index = {step_index}')
        

    
    
        ## full brain at once version
        # printlog("applying transforms....")
        # moving = ants.from_numpy(moving)  #apply transforms wants this format
        # moving.set_spacing((2.611, 2.611, 5, 1))
        # warped = ants.apply_transforms(fixed, moving, transforms, imagetype=3, interpolator='nearestNeighbor')
        # save_file = os.path.join(save_directory, 'brain_in_FDA.nii')
        # nib.Nifti1Image(warped.numpy(), np.eye(4)).to_filename(save_file)


        # printlog("applying transforms....")
        # #warp to first half of brain
        # first_quarter = int(dims[-1]/4)
        # printlog(f'first quarter of brain ends at {first_quarter}')
        # #first_quarter = 1000 ## testing how much it can do before failing, can't do 1000
        # moving1 = moving[:,:,:,:first_quarter]
        # moving1 = ants.from_numpy(moving1)
        # moving1.set_spacing((2.611, 2.611, 5, 1))
        # printlog(f'current memory{psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2}')
        # printlog('running warp 1')
        # warped_1 = ants.apply_transforms(fixed, moving1, transforms, imagetype=3, interpolator='nearestNeighbor')
        # #save_file = os.path.join(fly_directory, 'func_0', 'brain_in_FDA.nii')
        # printlog(f'shape warped {np.shape(warped_1)}')
        # printlog(f'shape moving {np.shape(moving1)}')
        # save_file_1 = os.path.join(save_directory, 'brain_in_FDA_1.nii') #first half
        # nib.Nifti1Image(warped_1.numpy(), np.eye(4)).to_filename(save_file_1)
        # printlog('saved first quarter')
        # printlog(f'memory before deletion{process.memory_info().rss/ (1024 * 1024)} in MB')  # in bytes
        # del warped_1
        # del moving1
        # gc.collect()
        # printlog(f'memory after deletion{process.memory_info().rss/ (1024 * 1024)} in MB')

        # ##second quarter
        # second_quarter = first_quarter*2
        # printlog(f'second quarter goes from {first_quarter} to {second_quarter}')
        # moving2 = moving[:,:,:,first_quarter:second_quarter]
        # moving2 = ants.from_numpy(moving2)
        # moving2.set_spacing((2.611, 2.611, 5, 1))
        # warped_2 = ants.apply_transforms(fixed, moving2, transforms, imagetype=3, interpolator='nearestNeighbor')
        # save_file_2 = os.path.join(save_directory, 'brain_in_FDA_2.nii') #second half
        # nib.Nifti1Image(warped_2.numpy(), np.eye(4)).to_filename(save_file_2)
        # printlog('saved second quarter')
        # del warped_2
        # del moving2
        # gc.collect()

        # ##third quarter
        # third_quarter = first_quarter*3
        # printlog(f'third quarter goes from {second_quarter} to {third_quarter}')
        # moving3 = moving[:,:,:,second_quarter:third_quarter]
        # moving3 = ants.from_numpy(moving3)
        # moving3.set_spacing((2.611, 2.611, 5, 1))
        # warped_3 = ants.apply_transforms(fixed, moving3, transforms, imagetype=3, interpolator='nearestNeighbor')
        # save_file_3 = os.path.join(save_directory, 'brain_in_FDA_3.nii') #second half
        # nib.Nifti1Image(warped_2.numpy(), np.eye(4)).to_filename(save_file_3)
        # printlog('saved third quarter')
        # del moving3
        # del warped_3
        # gc.collect()

        # ##4th quarter
        # printlog(f'fourth quarter goes from {third_quarter} to end')
        # moving4 = moving[:,:,:,third_quarter:]
        # moving4 = ants.from_numpy(moving4)
        # moving4.set_spacing((2.611, 2.611, 5, 1))
        # warped_4 = ants.apply_transforms(fixed, moving4, transforms, imagetype=3, interpolator='nearestNeighbor')
        # save_file_4 = os.path.join(save_directory, 'brain_in_FDA_4.nii') #second half
        # nib.Nifti1Image(warped_2.numpy(), np.eye(4)).to_filename(save_file_4)
        # printlog('saved 4th quarter')
        


        # #reopen warped 1-3 to concatenate
        # warped_1 = nib.load(save_file_1)
        # warped_2 = nib.load(save_file_2)
        # warped_3 = nib.load(save_file_3)
        # printlog('reopened first three warp files')

        # full_brain_warped = np.concatenate([warped_1, warped_2, warped_3, warped_4], axis = dims[-1])
        # printlog(f'shape warped brain= {np.shape(full_brain_warped)}, shape original brain = {np.shape(moving)}')
        # save_file_full = os.path.join(save_directory, 'brain_in_FDA.nii') #full
        # nib.Nifti1Image(full_brain_warped.numpy(), np.eye(4)).to_filename(save_file_full)
        # printlog('saved full brain')
    
    
    
    
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