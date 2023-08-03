
from sklearn.decomposition import IncrementalPCA
import os
import sys
import numpy as np
import argparse
import subprocess
import json
import time
import csv as csv
import scipy as scipy
from scipy.signal import find_peaks
import nibabel as nib
import h5py
from matplotlib import pyplot as plt
from xml.etree import ElementTree as ET

import pickle
import psutil
import math
import functions as fun
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
import brainsss

#sys.path.append(os.path.split(os.path.dirname(__file__))[0])



def main(args):
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']

    rerun_PCA = True #will look to see if PCA has already been run if False and not rerun. if true will rerun
    run_zscore = True #if true will run on zscore data and save as zscore pca otherwise will run on high pass
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')




    if run_zscore == False:
        key_to_run_PCA = 'high pass filter data' ##alternatively zscore data
        file_to_run_PCA = "MOCO_ch2_highpass.h5"
        save_name = "PCA_HP.h5" #change this if run zscore to keep track
    else:
        # file_to_run_PCA = "MOCO_ch2_highpass_zscore.h5"
        # key_to_run_PCA = 'zscore'
        # save_name = "PCA_zscore.h5"
        file_id = "zscore_rem_light.h5"  #put in PCA_main_switch.py 
        keys_to_run_PCA = ['20 zscore', '40 zscore', 'dark zscore']
        
    

    #print(f'Starting PCA on date: {date}')

    #find fly
    # all_files = os.listdir(directory)
    # filenames = [file for file in all_files if file_id in file]
    fly_files = os.listdir(directory)
    for brain_file in file_names:
        load_file = os.path.join(directory, brain_file)
        #check for high pass filter data (or zscore)
        save_name = str(brain_file[0:-3]) + "PCA.h5"
        save_file = os.path.join(directory, save_name)
        
    
        with h5py.File(load_file, 'r') as hf:
            load_keys = hf.keys()
            for key in keys_to_run_PCA:
                if key in load_keys:
                    printlog(f'Found {key} key!')

                    #check if PCA has already been run
                    if rerun_PCA == False and save_name in fly_files:
                        #also check that there is something in the PC file
                        with h5py.File(save_file, 'r') as c:
                            loadings_key = 'scores ' + str(key)
                            components_key = 'components' + str(key)
                            if loadings_key in c.keys():
                                printlog('PCA already exists ---> opening loadings and components for STA')
                                #open loadings and components
                                loadings = c[loadings_key][()]
                                reshaped_components = c[components_key][()]
                            else:
                                printlog('PCA file exists but no loadings key => runing again')
                                ## run PCA
                                loadings, reshaped_components = fun.run_PCA(load_file, 100, key)
                                printlog(f"PCA COMPLETED FOR {key}")
                                #save PCA info
                                with h5py.File(save_file, 'w') as f:
                                    fun.add_to_h5(save_file, loadings_key, loadings)
                                    fun.add_to_h5(save_file, components_key, reshaped_components)
                                    printlog(f'SAVED PCA loadings and components')
                    else:
                        ## run PCA
                        loadings, reshaped_components = fun.run_PCA(load_file, 100, key)
                        loadings_key = 'scores ' + str(key)
                        components_key = 'components' + str(key)
                        printlog(f"PCA COMPLETED FOR {key}")
                        #save PCA info
                        with h5py.File(save_file, 'w') as f:
                            fun.add_to_h5(save_file, loadings_key, loadings)
                            fun.add_to_h5(save_file, components_key, reshaped_components)
                            printlog(f'SAVED PCA loadings and components')




     

        # ##run peaks and make plots
        # ##get light_peaks!
        # light_peaks_adjusted = get_light_peaks(fly_directory)
        # bruker_framerate = get_Bruker_framerate(fly_directory)

        # if light_peaks_adjusted is not None: #if its not None
        #     #plot light peaks and save just to double check its ok
        #     fig1 = plt.figure()
        #     plt.scatter(light_peaks_adjusted, np.ones(len(light_peaks_adjusted)))
        #     plt.title('light peaks')
        #     fig1.savefig(os.path.join(fly_directory, 'light peaks check.png'))
        #     plt.show()

        #     abr_components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(0, reshaped_components.shape[3], 5)], axis=2) #5 is take every 5th z slice
        #     components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(0, reshaped_components.shape[3])], axis=2) #all z slices

        #     ## run STA on all loadings (don't actually need to have run light_peaks)
        #     ##reconsider bryans way of doing this to run on all loadings at once rather than in for loop. need to sort out shape
        #     all_loadings_trialed = []
        #     for loading_index in range(len(loadings[1])): #need it to run through n_components number of laodings 
        #         STA_trials = run_STA(fly_directory, loadings[:,loading_index])
        #         all_loadings_trialed.append(STA_trials)

        #     #save plotting components shape and light on times
        #     with h5py.File(save_file, 'a') as f:
        #         add_to_h5(save_file, 'abreviated components for plots', abr_components_shape_plotting)
        #         add_to_h5(save_file, 'all components for plots', components_shape_plotting)
        #         add_to_h5(save_file, 'bruker framerate', bruker_framerate)
        #         add_to_h5(save_file, 'light on times (s)', light_peaks_adjusted)


        #     ## add other plots later! (for now run in jupyter notebook)






if __name__=='__main__':
  main(json.loads(sys.argv[1]))
            