import time
import sys
import os
import re
import json
import datetime
import pyfiglet
import textwrap
import ..brainsss
import gc

modules = 'gcc/6.3.0 python/3.6.1 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36' 
#antspy/0.2.2'


## TO DO 
## SORT OUT FLIES AND FILES

#########################
### Setup preferences ###
#########################

width = 120 # width of print log
nodes = 1 # 1 or 2
nice = True #True # true to lower priority of jobs. ie, other users jobs go first
mem = 8 # number of CPUs #used for moco and zscore currently
mem_zscore = 20
bleaching_mem = 1

#moco parameters
timepoints = 6761 #number of volumes  Try to unhard-code this to match my actual brains
step = 10 #how many volumes one job will handle Luke recs 100 for functional and 10 for anatomical
time_moco = 10 #time in hours before it times out
time_zscore = 12 #time in hours before it times out

#####################
### Setup logging ###
#####################

logfile = './logs/' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
sys.stderr = brainsss.Logger_stderr_sherlock(logfile)

###################
### Setup paths ###
###################
##I want this to be the only place that there are filepaths

#CHANGE THESE PATHS
scripts_path = "/home/users/asmart/projects/brainsss_ash/scripts"
com_path = "/home/users/asmart/projects/brainsss_ash/scripts/com"

date = '20210719'
dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
flies_temp = os.listdir(dataset_path)  ## find directory names, they are the fly names
#to sort out non-fly directories (issue if I ever label a file with fly but I can't get isdir to work.)
flies = []
for i in flies_temp:
    if 'fly' in os.path.join(dataset_path, i):
        flies.append(i)

# if "stitched.nii" in file: 
#     stitched_file = True

stitched_string = 'stitched.nii'  #to find files that are stitched (used in bleaching)

mean_stitched_string = "stitched_mean.nii" #to get mean stitched brain  (not used yet)

any_stitched_string = 'stitched' #to find mean and non-mean (used in moco)

#Note: zscore still has a colors argument

###################
### Print Title ###
###################

title = pyfiglet.figlet_format("Brainsss", font="cyberlarge" ) #28 #shimrod
title_shifted = ('\n').join([' '*28+line for line in title.split('\n')][:-2])
printlog(title_shifted)
day_now = datetime.datetime.now().strftime("%B %d, %Y")
time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
printlog(F"{day_now+' | '+time_now:^{width}}")
printlog("")


######################
### Test vol moco ####
#######################
printlog(f"\n{'   vol by vol test   ':=^{width}}")
job_ids = []
for fly in flies:
    directory = os.path.join(dataset_path, fly)
    save_path = directory  #could have it save in a different folder in the future
    args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'colors': ['green'], file_names = [ch1_stitched.nii, ch2_stitched.nii], save_path = save_path}
    script = 'vol_moco.py'
    job_id = brainsss.sbatch(jobname='voltest',
                         script=os.path.join(scripts_path, script),
                         modules=modules,
                         args=args,
                         logfile=logfile, time=96, mem=mem, nice=nice, nodes=nodes)
    job_ids.append(job_id)

for job_id in job_ids:
    brainsss.wait_for_job(job_id, logfile, com_path)



#########################
## Create mean brains ###
#########################


printlog(f"\n{'   MEAN BRAINS   ':=^{width}}")
#files = ['functional_channel_1', 'functional_channel_2']
job_ids = []
for fly in flies:
    directory = os.path.join(dataset_path, fly)
    files = os.listdir(os.path.join(dataset_path, fly)) #to get the name of the files in each fly folder
    args = {'logfile': logfile, 'directory': directory, 'files': files}
    script = 'make_mean_brain.py'
    job_id = brainsss.sbatch(jobname='meanbrn',
                         script=os.path.join(scripts_path, script),
                         modules=modules,
                         args=args,
                         logfile=logfile, time=1, mem=1, nice=nice, nodes=nodes)
    job_ids.append(job_id)

for job_id in job_ids:
    brainsss.wait_for_job(job_id, logfile, com_path)


# # ###############
# # ### Fictrac ###
# # ###############

# # ### This will make some figures of your fictrac data
# # printlog(f"\n{'   FICTRAC QC   ':=^{width}}")
# # job_ids = []
# # for fly in flies:
# #     directory = os.path.join(dataset_path, fly, 'fictrac')
# #     if os.path.exists(directory):
# #         args = {'logfile': logfile, 'directory': directory}
# #         script = 'fictrac.py'
# #         job_id = brainsss.sbatch(jobname='fictrac',
# #                              script=os.path.join(scripts_path, script),
# #                              modules=modules,
# #                              args=args,
# #                              logfile=logfile, time=1, mem=1, nice=nice, nodes=nodes)
# #         job_ids.append(job_id)
# # for job_id in job_ids:
# #     brainsss.wait_for_job(job_id, logfile, com_path)




####################
### Bleaching QC ###
####################

### This will make a figure of bleaching

    
printlog(f"\n{'   BLEACHING QC   ':=^{width}}")
job_ids = []
for fly in flies:
    directory = os.path.join(dataset_path, fly)
    ### ADD FILES ARGUMENT TO BLEACHING AND FIND THE STITCHED BRAIN FILES TO RUN BLEACHING ON      
    all_files = os.listdir(os.path.join(dataset_path, fly)) #to get the name of the files in each fly folder
    files = []
    for file in all_files:
        if str(stitched_string) in file: #to get just stitched channels (to get mean brain stitched use "stitched_mean.nii")
            files.append(file)
    args = {'logfile': logfile, 'directory': directory, 'files': files}
    script = 'bleaching.py'
    job_id = brainsss.sbatch(jobname='bleachqc',
                         script=os.path.join(scripts_path, script),
                         modules=modules,
                         args=args,
                         logfile=logfile, time=1, mem=bleaching_mem, nice=nice, nodes=nodes)
    job_ids.append(job_id)
for job_id in job_ids:
    brainsss.wait_for_job(job_id, logfile, com_path)



##################
### Start MOCO ###
##################


printlog(f"\n{'   MOTION CORRECTION   ':=^{width}}")
# This will immediately launch all partial mocos and their corresponding dependent moco stitchers
                       
stitcher_job_ids = []
progress_tracker = {}
for fly in flies:
    directory = os.path.join(dataset_path, fly)
    fly_print = directory.split('/')[-1]

    moco_dir = os.path.join(directory, 'moco')
    if not os.path.exists(moco_dir):
        os.makedirs(moco_dir)

    starts = list(range(0,timepoints,step))
    stops = starts[1:] + [timepoints]
    
    all_files = os.listdir(os.path.join(dataset_path, fly)) #to get the name of the files in each fly folder
    files = []
    for file in all_files:
        if str(any_stitched_string) in file: #to get just stitched channels (mean and non-mean)
            files.append(file)
    printlog("MOCO files: ")
    for file in files:
        printlog(file)

    #######################
    ### Launch partials ###
    #######################
     
    job_ids = []
    for start, stop in zip (starts, stops):
        args = {'logfile': logfile, 'directory': directory, 'start': start, 'stop': stop, 'files': files}
        script = 'moco_partial.py'
        job_id = brainsss.sbatch(jobname='moco',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=time_moco, mem=mem, nice=nice, silence_print=True, nodes=nodes)
        job_ids.append(job_id)

    printlog(F"| moco_partials | SUBMITTED | {fly_print} | {len(job_ids)} jobs, {step} vols each |")
    job_ids_colons = ':'.join(job_ids)
    for_tracker = '/'.join(directory.split('/')[-2:])
    progress_tracker[for_tracker] = {'job_ids': job_ids, 'total_vol': timepoints}

    #################################
    ### Create dependent stitcher ###
    #################################

    args = {'logfile': logfile, 'directory': moco_dir}
    script = 'moco_stitcher.py'
    job_id = brainsss.sbatch(jobname='stitch',
                         script=os.path.join(scripts_path, script),
                         modules=modules,
                         args=args,
                         logfile=logfile, time=time_moco, mem=mem, dep=job_ids_colons, nice=nice, nodes=nodes)
    stitcher_job_ids.append(job_id)

if bool(progress_tracker): #if not empty
    brainsss.moco_progress(progress_tracker, logfile, com_path)

for job_id in stitcher_job_ids:
    brainsss.wait_for_job(job_id, logfile, com_path)

###############
### Z-Score ###
###############

printlog(f"\n{'   Z-SCORE   ':=^{width}}")
job_ids = []
for fly in flies:
    directory = os.path.join(dataset_path, fly)
    args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'colors': ['green', 'red']} #['ch1', 'ch2']} #moco.py will add color suffix and then moco_stitcher will save with that suffix
    script = 'zscore.py'
    job_id = brainsss.sbatch(jobname='zscore',
                         script=os.path.join(scripts_path, script),
                         modules=modules,
                         args=args,
                         logfile=logfile, time=time_zscore, mem=mem_zscore, nice=nice, nodes=nodes)
    job_ids.append(job_id)

for job_id in job_ids:
    brainsss.wait_for_job(job_id, logfile, com_path)

############
### Done ###
############

time.sleep(30) # to allow any final printing
day_now = datetime.datetime.now().strftime("%B %d, %Y")
time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
printlog("="*width)
printlog(F"{day_now+' | '+time_now:^{width}}")
