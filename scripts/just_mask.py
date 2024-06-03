"""Just run supervoxels based on new_align_process.py script"""


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
dates = ['20230504', '20230505', '20230714', '20230707'] 


for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    

    mem = 4
    high_pass_mem = 6
    super_mem = 20 #12 was insufficient for supervoxels 
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

    job_ids = []
    # for fly in func_flies:
    #     fly_number = get_fly_number(fly)
    #     #look at anat flies and find match
    #     for anat_fly in anat_flies:
    #         anat_number = get_fly_number(anat_fly)
    #         if anat_number == fly_number:
    #             current_anat_file = anat_fly

    #     func_directory = os.path.join(dataset_path, fly)
    #     anat_directory = os.path.join(dataset_path, current_anat_file)
    #     file_id = "mean.nii"
    #     #moco_id = "MOCO" #but everything after moco also has MOCO in it => need to specify files
    #     moco_files = ["MOCO_ch1.h5", "MOCO_ch2.h5"]

    #### make mask of hp moco zscore brain
    for fly in func_flies:
        ## should move file ids here later (for mean brain and brain to mask)
        # file_id = 'highpass_full_zscore_rem_light.h5'
        # all_files = os.listdir(func_directory)
        # file_names = [file for file in all_files if file_id in file]
        #args = {'logfile': logfile, 'directory': func_directory, 'file_names': file_names}
        func_directory = os.path.join(dataset_path, fly)
        args = {'logfile': logfile, 'directory': func_directory}
        script = 'mask.py'
        job_id = brainsss.sbatch(jobname='mask',
                            script=os.path.join(scripts_path, script),
                            modules=modules,
                            args=args,
                            logfile=logfile, time=2, mem=super_mem, nice=nice, nodes=nodes)
        brainsss.wait_for_job(job_id, logfile, com_path)

    time.sleep(30) # to allow any final printing
    day_now = datetime.datetime.now().strftime("%B %d, %Y")
    time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
    printlog("="*width)
    printlog(F"{day_now+' | '+time_now:^{width}}")

    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)