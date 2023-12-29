### creates STA for 40s and 20s eperiments seperately 
# and saves single z slices for each timepoint averaged across trials

## prob needs 12 mem

## from vscode
import os
import sys
import numpy as np
import h5py
import scipy as scipy
from scipy.signal import find_peaks
from matplotlib import pyplot as plt
import math
from xml.etree import ElementTree as ET
import csv as csv
from sklearn.decomposition import IncrementalPCA
import argparse
import subprocess
import json
import time
import nibabel as nib
import functions as fun
sys.path.append(os.path.split(os.path.dirname(__file__))[0])
import brainsss

def main(args):
    
    logfile = args['logfile']
    directory = args['directory'] # full fly path 
    file_names = args['file_names'] ## should be  _highpass.h5 now to run zscore on h5 files
    save_directory = args['save_path']

    
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    
    for brain_file in file_names:
        full_load_path = os.path.join(directory, brain_file)
        ##both 20 and 40s will be saved in this file
        save_file = os.path.join(save_directory, brain_file.split('.')[0] + '_STA.h5') #generate this file

        ##save pngs in seperate folder
        fig_save_path = os.path.join(save_directory, '/plots')
        if not os.path.exists(fig_save_path):
            os.mkdir(fig_save_path)

        #get light peaks in terms of brain time
        light_peaks_brain_t = fun.get_light_peaks_brain_t_no_bleedthrough (directory)
        print(np.shape(light_peaks_brain_t))

        ## get frames dark, 20, 40
        ## these are the start and stop points of the different experiments (have them be inclusive)
        brain_t_switch_indices = fun.get_brain_t_switch_set(directory)
        print(brain_t_switch_indices)

        #load brain
        with h5py.File(full_load_path, 'r') as hf:
            print(hf.keys())
            brain = hf['zscore']
            brain_dims = np.shape(brain)
            print('got the brain!')

            ##run through different experiments
            for exp in range(len(brain_t_switch_indices)):
                if exp == 0:
                    key_id = 'twenty'
                if exp == 1:
                    key_id = 'forty'
                
                exp_brain_t = brain_t_switch_indices[exp]

                trials = []
                for light_index in range(len(light_peaks_brain_t)-1):
                    current_light = light_peaks_brain_t[light_index]
                    next_light = light_peaks_brain_t[light_index + 1]
                    exp_shape = np.shape(exp_brain_t)
                    for round in range(exp_shape[0]): #to go through each set of exprs (20s usually has 3 and 40 has 2))
                        if exp_brain_t[round][0] <= current_light and next_light <= exp_brain_t[round][1]:  #starts and stops for each set
                            trial_data = brain[:,:,:,current_light:next_light]
                            trials.append(trial_data)
                print(f'{key_id} experiment trials collected')

                # add nans to sta to fix ragged array of trials 
                max_trial_time = max(len(t)for t in trials[0][0][0])

                max_trial_time = max(len(t)for t in trials[0][0][0])
                nan_brain = np.empty((len(trials), brain_dims[0], brain_dims[1], brain_dims[2],  max_trial_time)) * np.nan
                for i, trial in enumerate(trials): #[:,:,:]):
                    nan_brain[i, :,:,:, :trial.shape[3]] = trial
                print(np.shape(nan_brain))

                with h5py.File(save_file, 'w') as f:
                    fun.add_to_h5(save_file, f'{key_id} trials appended with nans', nan_brain)

                    mean_STA = np.nanmean(nan_brain, axis = 0)
                    print(np.shape(mean_STA))
                    fun.add_to_h5(save_file, f'{key_id} STA', mean_STA)
                    print(f'saved {key_id} STA')

                ## make plots! 7 x 7 grid of zslices
                for t in range(mean_STA.shape[3]):  # x, y, z, t
                    assert mean_STA.shape[2] == 49
                    rows = []
                    for row_ii in range(7):
                        row = []
                        for col_ii in range(7):
                            row.append(mean_STA[:, :, row_ii*7 + col_ii, t])
                        rows.append(np.concatenate(row, 1))  # if concatenate(row, 1) this makes the row horizontal. Could change.
                    mean_STA_tile = np.concatenate(rows, 2)  # this should always be a different axis from the one above.
                    plt.imshow(mean_STA_tile)
                    plt.title(f'STA {key_id}, t={t}')
                    brain_name = brain_file.split('.')[0]
                    save_title = f'{brain_name} STA {key_id} zscore brain t-{t}.png'
                    plt.savefig(os.path.join(fig_save_path, save_title), bbox_inches = 'tight')
                    
                    print(f'images saved for {key_id} experiment for {brain_file}')

if __name__ == '__main__':
    main(json.loads(sys.argv[1]))