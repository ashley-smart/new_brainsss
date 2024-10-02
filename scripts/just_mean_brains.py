""" 
THIS IS TO JUST MAKE MEANBRAINS. After this run clean anat on jupyter notebook. then run new_align_process


## this is the code that will run scripts to take an individual fly and run scripts to 
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
dates = [ '20240830'] #, '20230614'] #, '20230606', '20230609', '20230614', '20230407', '20230330', '20230616', '20230623', '20230630'] #'20230428', '20230616'] 








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
            


   

     




    
    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)