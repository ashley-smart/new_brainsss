"""align anatomical brain to functional brain and warp to brain template---based off of Luke's preprocess code. 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py

His instructions:
1) align func to anat (for an individual fly)
(brainsss function func2anat), see 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 507
can run using preprocess and the --f2a flag
2) align anat to whatever template you are using (the final space for your data). I use "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"
(brainsss function anat2anat), see 

https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 582
can run using preprocess and the --a2a flag

3) use these two transforms to apply to whatever neural data you want to warp. You can either warp in single maps you calculated in the original space (like a correlation map), or the entirety of your functional recording. For the former, the code will look something like
https://github.com/ClandininLab/brainsss/blob/main/brainsss/brain_utils.py
check out warp_STA_brain function.

If you want to warp the full recording, check out
https://github.com/lukebrez/dataflow/blob/master/sherlock_scripts/apply_transforms_to_raw_data.py
Make sure the voxel sizes are always set correctly, using
fixed.set_spacing(fixed_resolution)
and make sure the z-direction matches (ie either anterior to posterior or vica versa for the func,anat,and template.)

"""

import time
import sys
import os
import re
import json
import textwrap
import brainsss
import argparse
import nibabel as nib

def main(args):
    

    modules = 'gcc/6.3.0 python/3.6 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36 antspy/0.2.2'

    #########################
    ### Setup preferences ###
    #########################

    width = 120 # width of print log
    nodes = 2 # 1 or 2
    nice = True # true to lower priority of jobs. ie, other users jobs go first

    #####################
    ### Setup logging ###
    #####################

    logfile = './logs/' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    sys.stderr = brainsss.Logger_stderr_sherlock(logfile)
    brainsss.print_title(logfile, width)
    #################
    ### func2anat ###
    #################

    res_anat = (0.653, 0.653, 1)
    res_func = (2.611, 2.611, 5)

    for fly in fly_dirs:
        fly_directory = os.path.join(dataset_path, fly)

        if loco_dataset:
            moving_path = os.path.join(fly_directory, 'func_0', 'imaging', 'functional_channel_1_mean.nii')
        else:
            moving_path = os.path.join(fly_directory, 'func_0', 'moco', 'functional_channel_1_moc_mean.nii')
        moving_fly = 'func'
        moving_resolution = res_func

        if loco_dataset:
            fixed_path = os.path.join(fly_directory, 'anat_0', 'moco', 'stitched_brain_red_mean.nii')
        else:
            fixed_path = os.path.join(fly_directory, 'anat_0', 'moco', 'anatomy_channel_1_moc_mean.nii')
        fixed_fly = 'anat'
        fixed_resolution = res_anat

        save_directory = os.path.join(fly_directory, 'warp')
        if not os.path.exists(save_directory):
            os.mkdir(save_directory)

        type_of_transform = 'Affine'
        save_warp_params = True
        flip_X = False
        flip_Z = False

        low_res = False
        very_low_res = False

        iso_2um_fixed = True
        iso_2um_moving = False

        grad_step = 0.2
        flow_sigma = 3
        total_sigma = 0
        syn_sampling = 32

        args = {'logfile': logfile,
                'save_directory': save_directory,
                'fixed_path': fixed_path,
                'moving_path': moving_path,
                'fixed_fly': fixed_fly,
                'moving_fly': moving_fly,
                'type_of_transform': type_of_transform,
                'flip_X': flip_X,
                'flip_Z': flip_Z,
                'moving_resolution': moving_resolution,
                'fixed_resolution': fixed_resolution,
                'save_warp_params': save_warp_params,
                'low_res': low_res,
                'very_low_res': very_low_res,
                'iso_2um_fixed': iso_2um_fixed,
                'iso_2um_moving': iso_2um_moving,
                'grad_step': grad_step,
                'flow_sigma': flow_sigma,
                'total_sigma': total_sigma,
                'syn_sampling': syn_sampling}

        script = 'align_anat.py'
        job_id = brainsss.sbatch(jobname='align',
                                script=os.path.join(scripts_path, script),
                                modules=modules,
                                args=args,
                                logfile=logfile, time=8, mem=4, nice=nice, nodes=nodes) # 2 to 1
        brainsss.wait_for_job(job_id, logfile, com_path)
