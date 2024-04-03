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

"""this code will run warp_timeseries.py that Bella wrote to make a warped brain for a superfly
Will take the """
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append("/home/users/asmart/projects/new_brainsss/")
os.listdir("/home/users/asmart/projects/new_brainsss/")
sys.path.append("/home/users/asmart/projects/new_brainsss/brainsss")
import brainsss

modules = 'gcc/6.3.0 python/3.6.1 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36' 
scripts_path = "/home/users/asmart/projects/new_brainsss/scripts"
com_path = "/home/users/asmart/projects/new_brainsss/scripts/com"

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

title = pyfiglet.figlet_format("Brainsss", font="cyberlarge" ) #28 #shimrod
title_shifted = ('\n').join([' '*28+line for line in title.split('\n')][:-2])
printlog(title_shifted)
day_now = datetime.datetime.now().strftime("%B %d, %Y")
time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
printlog(F"{day_now+' | '+time_now:^{width}}")
printlog("")

##########################################################
#### extra functions #####
##########################
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
###############################################################

## run these dates
dates = ['20230714', '20230707', '20230505', '20230504', '20230428'] 
for date in dates:
    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    
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
    printlog(f'date {date}')
    printlog(f' func flies found: {func_flies}')


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
        file_id = "MOCO_ch2_highpass_full_zscore_rem_light.h5" ##run warp on this file
        moving_path = os.path.join(func_directory, file_id)
        #run warp timeseries
        args = {'logfile': logfile, 'directory': func_directory, 'moving_path': moving_path}
        script = 'warp_timeseries.py'
        job_id = brainsss.sbatch(jobname='warp_ts',
                            script=os.path.join(scripts_path, script),
                            modules=modules,
                            args=args,
                            logfile=logfile, time=3, mem=12, nice=nice, nodes=nodes) #, global_resources=True)
        job_ids.append(job_id)
        brainsss.wait_for_job(job_id, logfile, com_path)

    time.sleep(30) # to allow any final printing
    day_now = datetime.datetime.now().strftime("%B %d, %Y")
    time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
    printlog("="*width)
    printlog(F"{day_now+' | '+time_now:^{width}}")

    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)


    
