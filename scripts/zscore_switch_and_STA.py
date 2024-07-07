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


#dates = ['20230405__queue__', '20230330__queue__' ] #, '20230210_stitch']  #'20230124_stitch' didn't finish running zscore for first fly1-20s_0018 (2-27-23)
#dates = sys.argv  #input should be ['with date strings'] this doesnt work right

dates = ['20230505'] #, '20230512', '20230606', '20230609', '20230614', '20230407', '20230330', '20230616', '20230623', '20230630'] #'20230428', '20230616'] 
for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    

    mem = 12
    high_pass_mem = 6
    STA_mem = 18
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
    ### vol zscore ####
    #######################
    printlog(f"\n{'   vol by vol switch zscore   ':=^{width}}")
    #moco_names = ['MOCO_ch1.h5', 'MOCO_ch2.h5']   #run zscore on moco h5 files
    ##run zscore on high pass filtered moco files
    file_id = '_highpass.h5'  ##looks for this tag in filename and runs analysis on it
    job_ids = []
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
        all_files = os.listdir(directory)
        filenames = [file for file in all_files if file_id in file]
        if len(filenames) == 0: 
            printlog(f'NO {file_id} files! Cannot run zscore')
        args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'file_names': filenames, 'save_path': save_path}
        script = 'block_zscore.py'
        printlog(os.path.join(scripts_path, script))
        job_id = brainsss.sbatch(jobname='switch_zscore',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes)
        job_ids.append(job_id)
        printlog("fly started")



    ######################
    ### STA ####
    #######################
    printlog(f"\n{'   STA   ':=^{width}}")
    #moco_names = ['MOCO_ch1.h5', 'MOCO_ch2.h5']   #run zscore on moco h5 files
    ##run zscore on high pass filtered moco files
    file_id = 'highpass_full_zscore_rem_light.h5'  ##looks for this tag in filename and runs analysis on it
    job_ids = []
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
        all_files = os.listdir(directory)
        filenames = [file for file in all_files if file_id in file]
        if len(filenames) == 0: 
            printlog(f'NO {file_id} files! Cannot run STA')
        args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'file_names': filenames, 'save_path': save_path}
        script = 'STA.py'  ##this removes light frames
        printlog(os.path.join(scripts_path, script))
        job_id = brainsss.sbatch(jobname='STA',
                             script=os.path.join(scripts_path, script),
                             modules=modules,
                             args=args,
                             logfile=logfile, time=runtime, mem=STA_mem, nice=nice, nodes=nodes)
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



