""" ## this is the code that will run scripts to take an individual fly and run scripts to 
1) align individual fly functional channel to anatomical channel
use: "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"


## need to figure out if I use the t mean to align? 
    I think so
    should I use moco and hp filtered mean brain?
    can use make_mean_brain.py script, but need to add h5 condition
        can input file as arg

##need to write function to id same func and anat file



##this file will run other scripts 
#align_anat.py


align anatomical brain to functional brain and warp to brain template---based off of Bella's preprocess code. 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py

Bella instructions:
1) align func to anat (for an individual fly)
(brainsss function func2anat), see 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 507
can run using preprocess and the --f2a flag
2) align anat to whatever template you are using (the final space for your data). I use 
"/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"
(brainsss function anat2anat), see 

https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 582
can run using preprocess and the --a2a flag

3) use these two transforms to apply to whatever neural data you want to warp. You can either warp in single maps you calculated in the original space 
(like a correlation map), or the entirety of your functional recording. For the former, the code will look something like
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
import argparse
import nibabel as nib
import datetime
import pyfiglet
import textwrap
import gc


sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append("/home/users/asmart/projects/new_brainsss/")
os.listdir("/home/users/asmart/projects/new_brainsss/")
sys.path.append("/home/users/asmart/projects/new_brainsss/brainsss")

print(sys.path)
import brainsss

modules = 'gcc/6.3.0 python/3.6.1 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36' 



scripts_path = "/home/users/asmart/projects/new_brainsss/scripts"
com_path = "/home/users/asmart/projects/new_brainsss/scripts/com"

## extra functions
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



## run these dates
# '20230414',
dates = [ '20240802'] #, '20230614'] #, '20230606', '20230609', '20230614', '20230407', '20230330', '20230616', '20230623', '20230630'] #'20230428', '20230616'] 








for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    

    mem = 4
    high_pass_mem = 6
    mean_mem = 18 #12 got oom errors
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
    title = pyfiglet.figlet_format("Brainsss", font="cyberlarge" ) #28 #shimrod
    title_shifted = ('\n').join([' '*28+line for line in title.split('\n')][:-2])
    printlog(title_shifted)
    day_now = datetime.datetime.now().strftime("%B %d, %Y")
    time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
    printlog(F"{day_now+' | '+time_now:^{width}}")
    printlog("")

    printlog('looking for flies in date folder')
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
    printlog(f'date currently running: {date}')
    printlog(f' func flies to run: {func_flies}')


    

        
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
        printlog(f'first func directory {func_directory}')
        anat_directory = os.path.join(dataset_path, current_anat_file)
        file_id = "mean.nii"
        #moco_id = "MOCO" #but everything after moco also has MOCO in it => need to specify files
        moco_files = ["MOCO_ch1.h5", "MOCO_ch2.h5"]
        
        mean_func_file = [file for file in os.listdir(func_directory) if file_id in file]
        mean_anat_file = [file for file in os.listdir(anat_directory) if file_id in file]
        if len(mean_func_file) > 2 or len(mean_anat_file) > 2:
            printlog(f'ERROR: TOO many mean files. func = {mean_func_file}, anat = {mean_anat_file}')
        if len(mean_func_file) < 2: #==0:
            printlog(f'no {file_id} files for func. Running meanbrain')
            ##RUN MEAN BRAIN FOR FUNC
            #1. find moco files
            #moco_files = [file for file in os.listdir(func_directory) if moco_id in file]
            
            #2. get moco dir
            for file in moco_files: #two channels
                if file not in os.listdir(func_directory):
                    printlog(f'FILE NOT FOUND {file} cannot run func mean')

                moco_directory = os.path.join(func_directory, file)
                #3. run mean brain
                args = {'logfile': logfile, 'directory': func_directory, 'files': moco_files}
                script = 'make_mean_brain.py'
                job_id = brainsss.sbatch(jobname='meanbrn',
                                    script=os.path.join(scripts_path, script),
                                    modules=modules,
                                    args=args,
                                    logfile=logfile, time=3, mem=mean_mem, nice=nice, nodes=nodes) #, global_resources=True)
                job_ids.append(job_id)
                brainsss.wait_for_job(job_id, logfile, com_path)

        if len(mean_anat_file) < 2: #== 0:
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
                                logfile=logfile, time=3, mem=12, nice=nice, nodes=nodes) #), global_resources=True)
            job_ids.append(job_id)
            brainsss.wait_for_job(job_id, logfile, com_path)


        #need to regrab it so the new files appear if any of the above conditions were triggered
        mean_func_file = [file for file in os.listdir(func_directory) if file_id in file]
        mean_anat_file = [file for file in os.listdir(anat_directory) if file_id in file]
        #get paths for moving and fixed flies for alignment
        printlog(f'mean func files = {mean_func_file}')
        printlog(f'mean anat files = {mean_anat_file}')
        printlog('if the above != 2 each then the rest will not run')
        if len(mean_anat_file) == 2 and len(mean_func_file) == 2:
            
            ##then I can use them for the rest of the stuff
            ##need to get just channel 1!
            mean_ch1_func = [file for file in mean_func_file if 'ch1' in file][0]
            mean_ch1_anat = [file for file in mean_anat_file if 'ch1' in file][0] #[0] to get rid of brackets
            printlog(f'Setting the moving file {mean_ch1_func} and fixed file {mean_ch1_anat}')
            moving_path = os.path.join(func_directory, mean_ch1_func)
            fixed_path = os.path.join(anat_directory, mean_ch1_anat)
            printlog(f'moving path = {moving_path}')
            printlog(f'fixed path = {fixed_path}')
            


   

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

            warp_directory = os.path.join(func_directory, 'warp')
            if not os.path.exists(warp_directory):
                os.mkdir(warp_directory)

            args = {'logfile': logfile,
                    'save_directory': warp_directory, #want all transforms in warp folder for easy access
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
            res_meanbrain = (2,2,2) #this should change for new template right?
            res_meanbrain = (2.611, 2.611, 5)
            #res_atlas = (0.38,0.38,0.38) #not currenty used 
            res_atlas = (0.76,0.76,0.76) #for 76iso

            # for fly in fly_dirs:
                # fly_directory = os.path.join(dataset_path, fly)

                # if loco_dataset:
                #     moving_path = os.path.join(fly_directory, 'anat_0', 'moco', 'anat_red_clean.nii')
                # else:
                #     moving_path = os.path.join(fly_directory, 'anat_0', 'moco', 'anatomy_channel_1_moc_mean_clean.nii')
            
            clean_id = 'clean.nii'
            clean_file = [file for file in os.listdir(anat_directory) if clean_id in file]
            # run clean anat if it doesn't exist(gets rid of blobs around brain and does quantile normalization...)
            #  used for aligning to atlas
            #look for clean anat files
            if len(clean_file) == 0:
                printlog('no clean file found')
                preclean_id = 'mean.nii'  #I think I just want to run this on mean files
                preclean_files = [file for file in os.listdir(anat_directory) if preclean_id in file]
                #for mean_file in mean_files:
                printlog(f'These files: {preclean_files} will be cleaned')
                directory = anat_directory
                args = {'logfile': logfile, 'directory': directory, 'files': preclean_files}
                script = 'clean_anat.py'
                job_id = brainsss.sbatch(jobname='clnanat',
                                    script=os.path.join(scripts_path, script),
                                    modules=modules,
                                    args=args,
                                    logfile=logfile, time=1, mem=1, nice=nice, nodes=nodes)
                brainsss.wait_for_job(job_id, logfile, com_path)
            
            else:
                printlog(f'clean anat files found {clean_file}')
            clean_file_ch1 = [file for file in clean_file if 'ch1' in file]
            printlog(f'moving path: {os.path.join(anat_directory, clean_file_ch1[0])}')
            moving_path = os.path.join(anat_directory, clean_file_ch1[0]) #[0] to get rid of brackets
            moving_fly = 'anat'
            moving_resolution = res_anat

            # for gcamp6f with actual myr-tdtom
            #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"#luke.nii"
            #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/FDA_at_func_res_PtoA.nii"
            #fixed_fly = 'meanbrain'
            fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_076iso.nii"
            fixed_fly = 'FDA076iso'
            

            # for gcamp8s with non-myr-tdtom
            #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/20220421_make_nonmyr_meanbrain/non_myr_2_fdaatlas_40_8.nii"
            #fixed_fly = 'non_myr_mean'

            fixed_resolution = res_atlas

            warp_directory = os.path.join(func_directory, 'warp')
            if not os.path.exists(warp_directory):
                os.mkdir(warp_directory)

            type_of_transform = 'SyN'
            save_warp_params = True
            flip_X = False
            flip_Z = False

            low_res = False
            very_low_res = False

            iso_2um_fixed = False
            iso_2um_moving = False

            grad_step = 0.2
            flow_sigma = 3
            total_sigma = 0
            syn_sampling = 32

            args = {'logfile': logfile,
                    'save_directory': warp_directory,
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
            printlog(f'running align_anat template version with {fixed_fly}')
            job_id = brainsss.sbatch(jobname='align',
                                script=os.path.join(scripts_path, script),
                                modules=modules,
                                args=args,
                                logfile=logfile, time=8, mem=8, nice=nice, nodes=nodes)
            job_ids.append(job_id)
            brainsss.wait_for_job(job_id, logfile, com_path)

        



            # ############   YOU ARE HERE (commenting out bc error and I think does the same as warp_timeseries)
            # ####################################################
            # ### APPLY TRANSFORMS TO RAW DATA (MOCO, HP, ZSCORE) ##########
            # #####################################################
            # ## tips
            # ## fixed.set_spacing(fixed_resolution)
            # ## and make sure the z-direction matches (ie either anterior to posterior or vica versa for the func,anat,and template.)

            # warp_directory = os.path.join(func_directory, 'warp')
            # ## func_to_anat is saved differently because my func names are different...
            # func_fly_name = fly #the name of my fly (could also take last segment of func_directory)
            # anat_fly_name = current_anat_file #could also take last segment of anat_directory

            # args = {'logfile': logfile,
            #         'save_directory': func_directory, #currently saving in func, not sure if right spot...
            #         'warp_directory': warp_directory,
            #         'moving_path': moving_path,
            #         'fixed_fly': fixed_fly,
            #         'fixed_path': fixed_path,
            #         'moving_fly': moving_fly,
            #         'func_fly_name': func_fly_name,
            #         'anat_fly_name': anat_fly_name,
            #         'moving_resolution': moving_resolution,
            #         'fixed_resolution': fixed_resolution}
            
            # script = 'apply_transforms.py'
            # job_id = brainsss.sbatch(jobname='apply',
            #                         script=os.path.join(scripts_path, script),
            #                         modules=modules,
            #                         args=args,
            #                         logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes) # 2 to 1
            # brainsss.wait_for_job(job_id, logfile, com_path)
            # printlog(os.path.join(scripts_path, script))
            # job_ids.append(job_id)
            # printlog("fly started")



    #         ########################
    #         ### Apply transforms ###
    #         ########################
    #         res_func = (2.611, 2.611, 5)
    #         res_anat = (2,2,2)#(0.38, 0.38, 0.38)
    #         final_2um_iso = False #already 2iso so don't need to downsample #not sure what this is

    #         # for fly in fly_dirs:
    #             #fly_directory = os.path.join(dataset_path, fly)
    #         fly_directory = func_directory
    #         behaviors = ['dRotLabY', 'dRotLabZneg', 'dRotLabZpos'] #what are behaviors?
    #         for behavior in behaviors:
    #             if loco_dataset:
    #                 moving_path = os.path.join(fly_directory, 'func_0', 'corr', '20220418_corr_{}.nii'.format(behavior))
    #             else:
    #                 moving_path = os.path.join(fly_directory, 'func_0', 'corr', '20220420_corr_{}.nii'.format(behavior))
    #             moving_fly = 'corr_{}'.format(behavior)
    #             moving_resolution = res_func

    #             #fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/luke.nii"
    #             fixed_path = "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"#luke.nii"
    #             fixed_fly = 'meanbrain'
    #             fixed_resolution = res_anat

    #             save_directory = os.path.join(fly_directory, 'warp')
    #             if not os.path.exists(save_directory):
    #                 os.mkdir(save_directory)

    #             args = {'logfile': logfile,
    #                     'save_directory': save_directory,
    #                     'fixed_path': fixed_path,
    #                     'moving_path': moving_path,
    #                     'fixed_fly': fixed_fly,
    #                     'moving_fly': moving_fly,
    #                     'moving_resolution': moving_resolution,
    #                     'fixed_resolution': fixed_resolution,
    #                     'final_2um_iso': final_2um_iso}

    #             script = 'apply_transforms.py'
    #             job_id = brainsss.sbatch(jobname='aplytrns',
    #                                 script=os.path.join(scripts_path, script),
    #                                 modules=modules,
    #                                 args=args,
    #                                 logfile=logfile, time=12, mem=4, nice=nice, nodes=nodes) # 2 to 1
    #             brainsss.wait_for_job(job_id, logfile, com_path)

    #     ### STA version
    #     def warp_STA_brain(STA_brain, fly, fixed, anat_to_mean_type):
    #         n_tp = STA_brain.shape[1]
    #         dataset_path = '/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/20190101_walking_dataset'
    #         moving_resolution = (2.611, 2.611, 5)
    #         ###########################
    #         ### Organize Transforms ###
    #         ###########################
    #         warp_directory = os.path.join(dataset_path, fly, 'warp')
    #         warp_sub_dir = 'func-to-anat_fwdtransforms_2umiso'
    #         affine_file = os.listdir(os.path.join(warp_directory, warp_sub_dir))[0]
    #         affine_path = os.path.join(warp_directory, warp_sub_dir, affine_file)
    #         if anat_to_mean_type == 'myr':
    #             warp_sub_dir = 'anat-to-meanbrain_fwdtransforms_2umiso'
    #         elif anat_to_mean_type == 'non_myr':
    #             warp_sub_dir = 'anat-to-non_myr_mean_fwdtransforms_2umiso'
    #         else:
    #             print('invalid anat_to_mean_type')
    #             return
    #         syn_files = os.listdir(os.path.join(warp_directory, warp_sub_dir))
    #         syn_linear_path = os.path.join(warp_directory, warp_sub_dir, [x for x in syn_files if '.mat' in x][0])
    #         syn_nonlinear_path = os.path.join(warp_directory, warp_sub_dir, [x for x in syn_files if '.nii.gz' in x][0])
    #         ####transforms = [affine_path, syn_linear_path, syn_nonlinear_path]
    #         transforms = [syn_nonlinear_path, syn_linear_path, affine_path] ### INVERTED ORDER ON 20220503!!!!
    #         #ANTS DOCS ARE SHIT. THIS IS PROBABLY CORRECT, AT LEAST IT NOW WORKS FOR THE FLY(134) THAT WAS FAILING


    #         ### Warp timeponts
    #         warps = []
    #         for tp in range(n_tp):
    #             to_warp = np.rollaxis(STA_brain[:,tp,:,:],0,3)
    #             moving = ants.from_numpy(to_warp)
    #             moving.set_spacing(moving_resolution)
    #             ########################
    #             ### Apply Transforms ###
    #             ########################
    #             moco = ants.apply_transforms(fixed, moving, transforms)
    #             warped = moco.numpy()
    #             warps.append(warped)

    #         return warps



    #     #########################
    #     ###### make supervoxels
    #     ############################
    #         for func in funcs:
    #             args = {'logfile': logfile, 'func_path': func}
    #             script = 'make_supervoxels.py'
    #             job_id = brainsss.sbatch(jobname='supervox',
    #                                 script=os.path.join(scripts_path, script),
    #                                 modules=modules,
    #                                 args=args,
    #                                 logfile=logfile, time=2, mem=12, nice=nice, nodes=nodes)
    #             brainsss.wait_for_job(job_id, logfile, com_path)

    #     ############
    #     ### Done ###
    #     ############












    
    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)