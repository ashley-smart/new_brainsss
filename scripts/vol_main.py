## motion corrects, high pass filters, and zscores
## run new_align_process after this to align brains and make mean brains

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

dates = ['20231220__queue__' ]#, '20231215__queue__', '20231207__queue__']  #as of 4-27 4-5 still has one bad fly as does 330
for date in dates:

    dataset_path = "/oak/stanford/groups/trc/data/Ashley2/imports/" + str(date)
    #dataset_path = "/oak/stanford/groups/trc/data/krave/bruker_data/imports/" + str(date)

    zscore_switch = True ##if true runs zscore_switch code, if false runs zscore without switch
    fix_timestamps = False  ## change this in the future to check the date and after july 2023 have it set to false
    rem_light = True  #for zscore
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
    printlog(f"\n{'   running moco   ':=^{width}}")
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
    printlog(f"\n{'   high pass filter   ':=^{width}}")
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
    #     load_directory = os.path.join(func)
    #     save_directory = os.path.join(func)
        brain_file = ['MOCO_ch2.h5', 'MOCO_ch1.h5']

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
    printlog(f"\n{'   running zscore   ':=^{width}}")
    #moco_names = ['MOCO_ch1.h5', 'MOCO_ch2.h5']   #run zscore on moco h5 files
    ##run zscore on high pass filtered moco files
    file_id = '_highpass.h5'  ##looks for this tag in filename and runs analysis on it
    if zscore_switch == True and rem_light == True:
        zscore_sript = 'vol_zscore_rem_light.py'
    elif zscore_switch == True and rem_light == False:
        zscore_script = 'vol_zscore_switch.py'
    else:
        zscore_script = 'vol_zscore.py'
    printlog(f'zscore script running = {zscore_script}')


    #job_ids = []
    for fly in flies:
        directory = os.path.join(dataset_path, fly)
        save_path = directory  #could have it save in a different folder in the future
        all_files = os.listdir(directory)
        filenames = [file for file in all_files if file_id in file]
        args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'file_names': filenames, 'save_path': save_path, 'fix_timestamps': fix_timestamps}
        script = zscore_script
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


    ### make mean brain will run in next processing step new_align_process.py
        

    # ############################
    # #### make mean anat brain  ###
    # ################################
    # all_files = os.listdir(dataset_path)
    # anat_flies = []
    # func_flies = []
    # for file in all_files:
    #     fly_path = os.path.join(dataset_path, file)
    #     if 'anat' in fly_path and 'txt' not in fly_path:
    #         anat_flies.append(file)
    #     elif 'func' in fly_path:
    #         func_flies.append(file)

    # ##for now just making anat means
    # job_ids = []
    # for fly in anat_flies:
    #     directory = os.path.join(dataset_path, fly)
    #     files = os.listdir(directory)
    #     args = {'logfile': logfile, 'directory': directory, 'files': files} #note: files and flies
    #     script = 'make_mean_brain.py'
    #     job_id = brainsss.sbatch(jobname='meanbrn',
    #                         script=os.path.join(scripts_path, script),
    #                         modules=modules,
    #                         args=args,
    #                         logfile=logfile, time=5, mem=18, nice=nice, nodes=nodes)
    #     brainsss.wait_for_job(job_id, logfile, com_path)
    #     job_ids.append(job_id)
    #     printlog("fly started")

    # ########################
    # ###### PCA   ##########
    # ###########################
    # printlog(f"\n{'   PCA   ':=^{width}}")
    # file_id = '_highpass.h5'  ##doesn't currently do anything
    # job_ids = []
    # for fly in flies:
    #     directory = os.path.join(dataset_path, fly)
    #     save_path = directory  #could have it save in a different folder in the future
    #     all_files = os.listdir(directory)
    #     filenames = [file for file in all_files if file_id in file]  #I'm not suing this right now
    #     args = {'logfile': logfile, 'directory': directory, 'smooth': False, 'file_names': filenames, 'save_path': save_path}
    #     script = 'PCA_main.py'
    #     printlog(os.path.join(scripts_path, script))
    #     job_id = brainsss.sbatch(jobname='PCA',
    #                          script=os.path.join(scripts_path, script),
    #                          modules=modules,
    #                          args=args,
    #                          logfile=logfile, time=runtime, mem=mem, nice=nice, nodes=nodes)
    #     job_ids.append(job_id)
    #     printlog("fly started")

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



