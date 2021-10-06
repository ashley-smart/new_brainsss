import os
import sys
import json
from time import sleep
import datetime
import brainsss
import numpy as np
import nibabel as nib

def main(args):

    logfile = args['logfile']
    directory = args['directory'] # directory will be a full path to either an anat/imaging folder or a func/imaging folder
    files = args['files']
    width = 120
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')

    #files = ['functional_channel_1', 'functional_channel_2', 'anatomy_channel_1', 'anatomy_channel_2']
    
    #need to loop through all the files to stitch the brain, then I can make the means. 
    #can make the means from the stitched brains rather than the individual files. It will require storing more memory since will have to open both brains and store them
    #could save them and then reopen it
    full_brain_ch1 = []
    full_brain_ch2 = []
    for file in files:
        try:
            ## stitch brain ##
            if "channel_1" in file:
                brain_ch1 = np.asarray(nib.load(os.path.join(directory, file)).get_data(), dtype='uint16')
                full_brain_ch1.append(brain_ch1)
            elif "channel_2" in file:
                brain_ch2 = np.asarray(nib.load(os.path.join(directory, file)).get_data(), dtype='uint16')
                full_brain_ch2.append(brain_ch2)
     if len(full_breain_ch1) > 0:       
        stitched_brain_ch1 = np.concatenate(full_brain_ch1, axis = -1)
        #save stiched brain
        save_file = os.path.join(directory, '_ch1_stitched.nii')
        aff = np.eye(4)
        img = nib.Nifti1Image(meanbrain, aff)
        img.to_filename(save_file)
        
     if len(full_brain_ch2) > 0:
        stitched_brain_ch2 = np.concatenate(full_brain_ch2, axis = -1)
        #save stitched brain
        save_file = os.path.join(directory, '_ch2_stitched.nii')
        aff = np.eye(4)
        img = nib.Nifti1Image(meanbrain, aff)
        img.to_filename(save_file)
        
        
        
     for file in files:
        #only look at stitched brains
        if "stitched_" in file:
            ### make mean ###
            brain = np.asarray(nib.load(os.path.join(directory, file + '.nii')).get_data(), dtype='uint16')
            meanbrain = np.mean(brain, axis=-1)

            ### Save ###
            save_file = os.path.join(directory, file + '_mean.nii')
            aff = np.eye(4)
            img = nib.Nifti1Image(meanbrain, aff)
            img.to_filename(save_file)

            fly_func_str = ('|').join(directory.split('/')[-3:-1])
            fly_print = directory.split('/')[-3]
            func_print = directory.split('/')[-2]
            #printlog(f"COMPLETE | {fly_func_str} | {file} | {brain.shape} --> {meanbrain.shape}")
            printlog(F"meanbrn | COMPLETED | {fly_print} | {func_print} | {file} | {brain.shape} ===> {meanbrain.shape}")
            print(brain.shape[-1]) ### IMPORTANT: for communication to main
        except FileNotFoundError:
            printlog(F"Not found (skipping){file:.>{width-20}}")
            #printlog(f'{file} not found.')

if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
