""" ## this is the code that will run scripts to take an individual fly and run scripts to 
1) align individual fly functional channel to anatomical channel
use: "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"


## need to figure out if I use the t mean to align? 
    I think so
    should I use moco and hp filtered mean brain?
    can use make_mean_brain.py script, but need to add h5 condition
        can input file as arg

##need to write function to id same func and anat file

"""

import time
import sys
import os
import re
import json
import textwrap
import argparse
import nibabel as nib
import datetime
import pyfiglet
import textwrap
import gc


sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append('/home/users/asmart/projects/new_brainsss/')
print(sys.path)
import brainsss

modules = 'gcc/6.3.0 python/3.6.1 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36' 



scripts_path = "/home/users/asmart/projects/new_brainsss/scripts"
com_path = "/home/users/asmart/projects/new_brainsss/scripts/com"

def get_fly_number (file):
    """looks for "fly" in file and returns number following"""
    if 'fly' not in file or '_' not in file:
        print(f'ERROR: No appropriate flyid found in "{file}"')
        return None
    else:
        number_start = file.find('fly') + 3
        first_hyphen = file.find('_')
        number = file[number_start:first_hyphen]
        return number


dates = ['20230504', '20230428', '20230616'] 
for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    

    mem = 4
    high_pass_mem = 6
    runtime = 8 #144 #time in hours before it stops running  use 48 for normal partition
    width = 120 # width of print log
    nodes = 1 # 1 or 2
    nice = True #True # true to lower priority of jobs. ie, other users jobs go first



    #####################
    ### Setup logging ###
    #####################

    logfile = './logs/' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    sys.stderr = brainsss.Logger_stderr_sherlock(logfile)


    ###################################
    ## look for flies in date folder ##
    ###################################

    flies_temp = os.listdir(dataset_path)  ## find directory names, they are the fly names
    #to sort out non-fly directories (issue if I ever label a file with fly but I can't get isdir to work.)
    func_flies = []
    anat_flies = []
    for i in flies_temp:
        #if 'fly' in os.path.join(dataset_path, i):
        fly_path = os.path.join(dataset_path, i)
        if 'fly' in fly_path and 'anat' not in fly_path and 'json' not in fly_path and 'func' in fly_path: #to avoid anat
            func_flies.append(i)
        elif 'fly' in fly_path and 'anat' in fly_path and 'json' not in fly_path: ##need to get anat
            anat_flies.append(i)
    printlog(str(date))
    printlog(str(func_flies))


    title = pyfiglet.figlet_format("Brainsss", font="cyberlarge" ) #28 #shimrod
    title_shifted = ('\n').join([' '*28+line for line in title.split('\n')][:-2])
    printlog(title_shifted)
    day_now = datetime.datetime.now().strftime("%B %d, %Y")
    time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
    printlog(F"{day_now+' | '+time_now:^{width}}")
    printlog("")

        
    ####################################################
    ####  check mean brain exsts or make it ##########
    #####################################################
    #1. look for mean brain for ch1 for func and anat
    # 2. make mean brain if it doesn't exist
    # otherwise use that as file id 
    job_ids = []
    for fly in func_flies:
        fly_number = get_fly_number(fly)
        #look at anat flies and find match
        for anat_fly in anat_flies:
            anat_number = get_fly_number(anat_fly)
            if anat_number == fly_number:
                current_anat_file = anat_fly

        func_directory = os.path.join(dataset_path, fly)
        anat_directory = os.path.join(dataset_path, current_anat_file)
        file_id = "mean.h5"
        moco_id = "moco.h5"
        
        mean_func_file = [file for file in os.listdir(func_directory) if file_id in file]
        mean_anat_file = [file for file in os.listdir(anat_directory) if file_id in file]
        if len(mean_func_file) > 2 or len(mean_anat_file) > 2:
            printlog(f'ERROR: TOO many mean files. func = {mean_func_file}, anat = {mean_anat_file}')
        if len(mean_func_file) == 0:
            printlog(f'no {file_id} files for func. Running meanbrain')
            ##RUN MEAN BRAIN FOR FUNC
            #1. find moco files
            moco_files = [file for file in os.listdir(func_directory) if moco_id in file]
            #2. get moco dir
            for file in moco_files: #two channels
                moco_directory = os.path.join(func_directory, file)
                #3. run mean brain
                args = {'logfile': logfile, 'directory': moco_directory, 'files': files}
                script = 'make_mean_brain.py'
                job_id = brainsss.sbatch(jobname='meanbrn',
                                    script=os.path.join(scripts_path, script),
                                    modules=modules,
                                    args=args,
                                    logfile=logfile, time=3, mem=12, nice=nice, nodes=nodes, global_resources=True)
                job_ids.append(job_id)
                brainsss.wait_for_job(job_id, logfile, com_path)

        if len(mean_anat_file) == 0:
            printlog(f'no {file_id} files for anat. Running meanbrain')
            ##run mean brain for anat
            #will not have moco
            raw_id = 'stitched.nii'
            files = [file for file in os.listdir(anat_directory) if raw_id in file]
            #for file in moco_files: #two channels
            directory = anat_directory
            #3. run mean brain
            args = {'logfile': logfile, 'directory': directory, 'files': files}
            script = 'make_mean_brain.py'
            job_id = brainsss.sbatch(jobname='meanbrn',
                                script=os.path.join(scripts_path, script),
                                modules=modules,
                                args=args,
                                logfile=logfile, time=3, mem=12, nice=nice, nodes=nodes, global_resources=True)
            job_ids.append(job_id)
            brainsss.wait_for_job(job_id, logfile, com_path)



            ### I PROBABLY WANT TO RUN CLEAN_ANAT as well
            ##########  clean anat (gets rid of blobs around brain and does quantile normalization...)
            #######################################
            #  used for aligning to atlas, but I think Luke does not use to align to func for individual fly

            preclean_id = 'mean.nii'  #I think I just want to run this on mean files
            preclean_files = [file for file in os.listdir(anat_directory) if preclean_id in file]
            #for mean_file in mean_files:
            directory = anat_directory
            args = {'logfile': logfile, 'directory': directory, 'files': preclean_files}
            script = 'clean_anat.py'
            job_id = brainsss.sbatch(jobname='clnanat',
                                script=os.path.join(scripts_path, script),
                                modules=modules,
                                args=args,
                                logfile=logfile, time=1, mem=1, nice=nice, nodes=nodes)
            brainsss.wait_for_job(job_id, logfile, com_path)



        if len(mean_anat_file) == 2 and len(mean_func_file) == 2:
            ##then I can use them for the rest of the stuff
            ##need to get just channel 1!!!!
            mean_ch1_func = [file for file in mean_func_file if 'ch1' in file]
            mean_ch1_anat = [file for file in mean_anat_file if 'ch1' in file]
            
            moving_path = os.path.join(func_directory, mean_ch1_func)
            fixed_path = os.path.join(anat_directory, mean_ch1_anat)



   

            #################################################
            #### align individual fly func to anat  ######
            ############################################
            res_anat = (0.653, 0.653, 1)
            res_func = (2.611, 2.611, 5)
            
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
                    'save_directory': func_directory, #save_directory,
                    'fixed_path': fixed_path,
                    'moving_path': moving_path,
                    'fixed_fly': anat_directory, #fixed_fly,
                    'moving_fly': func_directory, #moving_fly,
                    'type_of_transform': type_of_transform,
                    'flip_X': flip_X,
                    'flip_Z': flip_Z,
                    'moving_resolution': res_func,
                    'fixed_resolution': res_anat,
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
                                    logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes) # 2 to 1
            brainsss.wait_for_job(job_id, logfile, com_path)
            printlog(os.path.join(scripts_path, script))
            job_ids.append(job_id)
            printlog("fly started")





           

            #############################################
            ## align anatomical to template ##############
            #########################################

            #res_anat = (1.3,1.3,1.3) # new anat res <------------------ this is set !!!!!
            res_anat = (0.653, 0.653, 1)
            res_meanbrain = (2,2,2)

            # for fly in fly_dirs:
                # fly_directory = os.path.join(dataset_path, fly)

                # if loco_dataset:
                #     moving_path = os.path.join(fly_directory, 'anat_0', 'moco', 'anat_red_clean.nii')
                # else:
                #     moving_path = os.path.join(fly_directory, 'anat_0', 'moco', 'anatomy_channel_1_moc_mean_clean.nii')
            
            clean_id = 'clean.nii'
            clean_file = [file for file in os.listdir(anat_directory) if clean_id in file]
            moving_path = os.path.join(anat_directory, clean_file)
            
            moving_fly = 'anat'
            moving_resolution = res_anat

            # for gcamp6f with actual myr-tdtom
            fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"#luke.nii"
            fixed_fly = 'meanbrain'

            # for gcamp8s with non-myr-tdtom
            #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/20220421_make_nonmyr_meanbrain/non_myr_2_fdaatlas_40_8.nii"
            #fixed_fly = 'non_myr_mean'

            fixed_resolution = res_meanbrain

            save_directory = os.path.join(func_directory, 'warp')
            if not os.path.exists(save_directory):
                os.mkdir(save_directory)

            type_of_transform = 'SyN'
            save_warp_params = True
            flip_X = False
            flip_Z = False

            low_res = False
            very_low_res = False

            iso_2um_fixed = False
            iso_2um_moving = True

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
                                logfile=logfile, time=8, mem=8, nice=nice, nodes=nodes)
            job_ids.append(job_id)
            brainsss.wait_for_job(job_id, logfile, com_path)

        



            ############   YOU ARE HERE 
































            # ########################
            # ### Apply transforms ###
            # ########################
            # res_func = (2.611, 2.611, 5)
            # res_anat = (2,2,2)#(0.38, 0.38, 0.38)
            # final_2um_iso = False #already 2iso so don't need to downsample #not sure what this is

            # # for fly in fly_dirs:
            #     #fly_directory = os.path.join(dataset_path, fly)
            # fly_directory = func_directory
            # behaviors = ['dRotLabY', 'dRotLabZneg', 'dRotLabZpos'] #what are behaviors?
            # for behavior in behaviors:
            #     if loco_dataset:
            #         moving_path = os.path.join(fly_directory, 'func_0', 'corr', '20220418_corr_{}.nii'.format(behavior))
            #     else:
            #         moving_path = os.path.join(fly_directory, 'func_0', 'corr', '20220420_corr_{}.nii'.format(behavior))
            #     moving_fly = 'corr_{}'.format(behavior)
            #     moving_resolution = res_func

            #     #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/luke.nii"
            #     fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"#luke.nii"
            #     fixed_fly = 'meanbrain'
            #     fixed_resolution = res_anat

            #     save_directory = os.path.join(fly_directory, 'warp')
            #     if not os.path.exists(save_directory):
            #         os.mkdir(save_directory)

            #     args = {'logfile': logfile,
            #             'save_directory': save_directory,
            #             'fixed_path': fixed_path,
            #             'moving_path': moving_path,
            #             'fixed_fly': fixed_fly,
            #             'moving_fly': moving_fly,
            #             'moving_resolution': moving_resolution,
            #             'fixed_resolution': fixed_resolution,
            #             'final_2um_iso': final_2um_iso}

            #     script = 'apply_transforms.py'
            #     job_id = brainsss.sbatch(jobname='aplytrns',
            #                         script=os.path.join(scripts_path, script),
            #                         modules=modules,
            #                         args=args,
            #                         logfile=logfile, time=12, mem=4, nice=nice, nodes=nodes) # 2 to 1
            #     brainsss.wait_for_job(job_id, logfile, com_path)

        
        ##########################
        # ###### make supervoxels
        # ############################
        #     for func in funcs:
        #         args = {'logfile': logfile, 'func_path': func}
        #         script = 'make_supervoxels.py'
        #         job_id = brainsss.sbatch(jobname='supervox',
        #                             script=os.path.join(scripts_path, script),
        #                             modules=modules,
        #                             args=args,
        #                             logfile=logfile, time=2, mem=12, nice=nice, nodes=nodes)
        #         brainsss.wait_for_job(job_id, logfile, com_path)

        ############
        ### Done ###
        ############












    
    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)