import time
import sys
import os
import re
import json
import textwrap
import datetime

import argparse

sys.path.append(os.path.split(os.path.dirname(__file__))[0])
print(sys.path)
import brainsss

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
scripts_path = '/home/users/asmart/projects/new_brainsss/scripts'
com_path = os.path.join(scripts_path, 'com')

###########################
### Run make mean brain ###
###########################

dates = ['20230330']

for date in dates: 
    dataset_path = '/oak/stanford/groups/trc/data/Ashley2/imports/' + str(date) + '/'
    all_files = os.listdir(dataset_path)
    anat_flies = []
    func_flies = []
    for file in all_files:
        fly_path = os.path.join(dataset_path, file)
        if 'anat' in fly_path:
            anat_flies.append(file)
        elif 'func' in fly_path:
            func_flies.append(file)

    ##for now just making anat means
    for fly in anat_flies:
        directory = os.path.join(dataset_path, fly)
        files = os.listdir(directory)
        args = {'logfile': logfile, 'directory': directory, 'files': files} #note: files and flies
        script = 'make_mean_brain.py'
        job_id = brainsss.sbatch(jobname='meanbrn',
                            script=os.path.join(scripts_path, script),
                            modules=modules,
                            args=args,
                            logfile=logfile, time=5, mem=18, nice=nice, nodes=nodes, global_resources=True)
        brainsss.wait_for_job(job_id, logfile, com_path)