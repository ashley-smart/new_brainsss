## to be sure I'm running just vol_moco



import time
import sys
import os
import re
import json
import datetime
import pyfiglet
import textwrap
import gc

sys.path.append(os.path.split(os.path.dirname(__file__))[0])
print(sys.path)
import brainsss

modules = 'gcc/6.3.0 python/3.6.1 py-numpy/1.14.3_py36 py-pandas/0.23.0_py36 viz py-scikit-learn/0.19.1_py36' 



scripts_path = "/home/users/asmart/projects/new_brainsss/scripts"
com_path = "/home/users/asmart/projects/new_brainsss/scripts/com"


dates = ['20230130_stitch', '20230210_stitch']  #'20230124_stitch' didn't finish running zscore for first fly1-20s_0018 (2-27-23)
#dates = ['20211217', '20211210', '20211208', '20211115']
for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    #dataset_path = "/oak/stanford/groups/trc/data/krave/bruker_data/imports/" + str(date)


    mem = 4
    high_pass_mem = 6
    runtime = 48 #144 #time in hours before it stops running  use 48 for normal partition
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
    flies = []
    for i in flies_temp:
        #if 'fly' in os.path.join(dataset_path, i):
        fly_path = os.path.join(dataset_path, i)
        if 'fly' in fly_path and 'anat' not in fly_path and 'json' not in fly_path: #to avoid anat
            flies.append(i)
    printlog(str(date))
    printlog(str(flies))


    title = pyfiglet.figlet_format("Brainsss", font="cyberlarge" ) #28 #shimrod
    title_shifted = ('\n').join([' '*28+line for line in title.split('\n')][:-2])
    printlog(title_shifted)
    day_now = datetime.datetime.now().strftime("%B %d, %Y")
    time_now = datetime.datetime.now().strftime("%I:%M:%S %p")
    printlog(F"{day_now+' | '+time_now:^{width}}")
    printlog("")


    ######################
    ### vol moco ####
    #######################
    printlog(f"\n{'   vol by vol moco test   ':=^{width}}")
    job_ids = []
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
        args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'colors': ['green'], 'file_names': ['ch1_stitched.nii', 'ch2_stitched.nii'], 'save_path': save_path}
        script = 'vol_moco.py'
        job_id = brainsss.sbatch(jobname='volmoco',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes)
        job_ids.append(job_id)

    for job_id in job_ids:
        brainsss.wait_for_job(job_id, logfile, com_path)
        
    ###############################
    ## high pass temporal filter ##
    ################################
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
    #     load_directory = os.path.join(func)
    #     save_directory = os.path.join(func)
        brain_file = 'MOCO_ch2.h5'

        args = {'logfile': logfile, 'load_directory': directory, 'save_directory': save_path, 'brain_file': brain_file}
        script = 'temporal_high_pass_filter.py'
        job_id = brainsss.sbatch(jobname='highpass',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=4, mem=high_pass_mem, nice=nice, nodes=nodes)
        brainsss.wait_for_job(job_id, logfile, com_path)


    ######################
    ### vol zscore ####
    #######################
    printlog(f"\n{'   vol by vol zscore test   ':=^{width}}")
    moco_names = ['MOCO_ch1.h5', 'MOCO_ch2.h5']   #run zscore on moco h5 files
    job_ids = []
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
        args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'colors': ['green'], 'file_names': moco_names, 'save_path': save_path}
        script = 'vol_zscore.py'
        printlog(os.path.join(scripts_path, script))
        job_id = brainsss.sbatch(jobname='volzscore',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes)
        job_ids.append(job_id)
        printlog("fly started")

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



