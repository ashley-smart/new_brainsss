
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

#sys.path.append(os.path.split(os.path.dirname(__file__))[0])



def main(args):
    #load_directory = args['load_directory']
    directory = args['directory']
    #save_directory = args['save_directory']
    #brain_files = args['brain_file']

    rerun_PCA = True #will look to see if PCA has already been run if False and not rerun. if true will rerun
    run_zscore = False #if true will run on zscore data and save as zscore pca otherwise will run on high pass

    if run_zscore == False:
        key_to_run_PCA = 'high pass filter data' ##alternatively zscore data
        file_to_run_PCA = "MOCO_ch2_highpass.h5"
        save_name = "PCA_HP.h5" #change this if run zscore to keep track
    else:
        file_to_run_PCA = "MOCO_ch2_highpass_zscore.h5"
        key_to_run_PCA = 'zscore'
        save_name = "PCA_zscore.h5"
    

    
    #find fly
    all_files = os.listdir(directory)
    for file in all_files:
        if 'fly' in file and 'func' in file:  ##Note: won't find flies that don't have func in name of folder
            printlog(f'found fly! running on {file}')
            fly_name = file
            fly_directory = os.path.join(directory, fly_name)
            # save_plots = '/oak/stanford/groups/trc/data/Ashley2/imports/' + str(date) + "_PLOTS/" + str(fly_name)
            # if not os.path.exists(save_plots):  #I'm getting a permission denied error in sherlock. Not sure why. maybe weird permission issues?
            #     os.makedirs(save_plots)

            #check for high pass filter data (or later zscore)

            fly_path = os.path.join(fly_directory, file_to_run_PCA)
        
            with h5py.File(fly_path, 'r') as hf:
                keys = hf.keys()
                if key_to_run_PCA in keys:
                    printlog(f'Found {key_to_run_PCA} key!')
                else:
                    printlog(f'ERROR: no {key_to_run_PCA} for this fly {fly_name}')
                    break

            ##check if shoudl run PCA or already ran
            save_file = os.path.join(fly_directory, save_name)
            fly_files = os.listdir(fly_directory)
            if rerun_PCA == False and save_name in fly_files:
                #also check that there is something in the PC file
                with h5py.File(save_file, 'r') as c:
                    if 'scores' in c.keys():
                        printlog('PCA already exists ---> opening loadings and components for STA')
                        #open loadings and components
                        loadings = c['scores'][()]
                        reshaped_components = c['components'][()]
                    else:
                        printlog('PCA file exists but no loadings key => runing again')
                        ## run PCA
                        loadings, reshaped_components = run_PCA(fly_path, 100, key_to_run_PCA)
                        printlog(f"PCA COMPLETED FOR {fly_name}")
                        #save PCA info
                        with h5py.File(save_file, 'w') as f:
                            add_to_h5(save_file, 'scores', loadings)
                            add_to_h5(save_file, 'components', reshaped_components)
                            printlog(f'SAVED PCA loadings and components')
            else:
                ## run PCA
                loadings, reshaped_components = run_PCA(fly_path, 100, key_to_run_PCA)
                printlog(f"PCA COMPLETED FOR {fly_name}")
                #save PCA info
                with h5py.File(save_file, 'w') as f:
                    add_to_h5(save_file, 'scores', loadings)
                    add_to_h5(save_file, 'components', reshaped_components)
                    printlog(f'SAVED PCA loadings and components')

            ##run peaks and make plots
            ##get light_peaks!
            light_peaks_adjusted = get_light_peaks(fly_directory)
            bruker_framerate = get_Bruker_framerate(fly_directory)

            if light_peaks_adjusted is not None: #if its not None
                #plot light peaks and save just to double check its ok
                fig1 = plt.figure()
                plt.scatter(light_peaks_adjusted, np.ones(len(light_peaks_adjusted)))
                plt.title('light peaks')
                fig1.savefig(os.path.join(fly_directory, 'light peaks check.png'))
                plt.show()

                abr_components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(0, reshaped_components.shape[3], 5)], axis=2) #5 is take every 5th z slice
                components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(0, reshaped_components.shape[3])], axis=2) #all z slices

                ## run STA on all loadings (don't actually need to have run light_peaks)
                ##reconsider bryans way of doing this to run on all loadings at once rather than in for loop. need to sort out shape
                all_loadings_trialed = []
                for loading_index in range(len(loadings[1])): #need it to run through n_components number of laodings 
                    STA_trials = run_STA(fly_directory, loadings[:,loading_index])
                    all_loadings_trialed.append(STA_trials)

                #save plotting components shape and light on times
                with h5py.File(save_file, 'a') as f:
                    add_to_h5(save_file, 'abreviated components for plots', abr_components_shape_plotting)
                    add_to_h5(save_file, 'all components for plots', components_shape_plotting)
                    add_to_h5(save_file, 'bruker framerate', bruker_framerate)
                    add_to_h5(save_file, 'light on times (s)', light_peaks_adjusted)


                ## add other plots later! (for now run in jupyter notebook)


## get light peaks
## functions
## get data out of voltage file     
#get just diode column
def get_diode_column(raw_light_data):
    """light data should be single fly and have the header be the first row"""
    header = raw_light_data[0]
    diode_column = []
    for i in range(len(header)):
        #if 'diode' in header[i]:
        if 'Input 0' in header[i]: #for new split straagey
            diode_column = i
    reshape_light_data = np.transpose(raw_light_data[1:])
    column = reshape_light_data[:][diode_column] #don't want header anymore
    column = [float(i) for i in column] #for some reason it was saved as string before
    return column


## get xml timestamps
def load_timestamps(directory, file='functional.xml'):
    """ Parses a Bruker xml file to get the times of each frame, or loads h5py file if it exists.
    First tries to load from 'timestamps.h5' (h5py file). If this file doesn't exist
    it will load and parse the Bruker xml file, and save the h5py file for quick loading in the future.
    Parameters
    ----------
    directory: full directory that contains xml file (str).
    file: Defaults to 'functional.xml'
    Returns
    -------
    timestamps: [t,z] numpy array of times (in ms) of Bruker imaging frames.
    """
    try:
        #print('Trying to load timestamp data from hdf5 file.')
        with h5py.File(os.path.join(directory, 'timestamps.h5'), 'r') as hf:
            timestamps = hf['timestamps'][:]

    except:
        print('Failed. Extracting frame timestamps from bruker xml file.')
        xml_file = os.path.join(directory, file)
        tree = ET.parse(xml_file)
        root = tree.getroot()
        timestamps = []
        
        sequences = root.findall('Sequence')
        for sequence in sequences:
            frames = sequence.findall('Frame')
            for frame in frames:
                filename = frame.findall('File')[0].get('filename')
                time = float(frame.get('relativeTime'))
                timestamps.append(time)
        timestamps = np.multiply(timestamps, 1000)

        if len(sequences) > 1:
            timestamps = np.reshape(timestamps, (len(sequences), len(frames)))
        else:
            timestamps = np.reshape(timestamps, (len(frames), len(sequences)))

        ### Save h5py file ###
        with h5py.File(os.path.join(directory, 'timestamps.h5'), 'w') as hf:
            hf.create_dataset("timestamps", data=timestamps)
    
    #print('Success.')
    return timestamps


 
# # get light peaks/s

# #get voltage file
# data_reducer = 100
# light_data = []
# with open(voltage_path, 'r') as rawfile:
#     reader = csv.reader(rawfile)
#     data_single = []
#     for i, row in enumerate(reader):
#         if i % data_reducer == 0: #will downsample the data 
#             data_single.append(row)
#     #light_data.append(data_single) #for more than one fly
#     light_data = data_single
 

        

# light_column = get_diode_column(light_data)
# print(np.shape(light_column))
    
# # find peaks
# light_median = np.median(light_column)
# early_light_max = max(light_column[0:2000])
# light_peaks, properties = scipy.signal.find_peaks(light_column, height = early_light_max +.001, prominence = .1, distance = 10)
   
    
    
# ## convert to seconds
# voltage_framerate =  10000/data_reducer #frames/s # 1frame/.1ms * 1000ms/1s = 10000f/s
# light_peaks_adjusted = light_peaks/voltage_framerate
# print('voltage framerate =', voltage_framerate)


# #store light_peaks_adjusted in new h5 file


def get_light_peaks (Path):
    """input fly path and get out the light peaks files in seconds"""
    data_reducer = 100
    light_data = []
    voltage_path = find_voltage_file(Path)
    with open(voltage_path, 'r') as rawfile:
        reader = csv.reader(rawfile)
        data_single = []
        for i, row in enumerate(reader):
            if i % data_reducer == 0: #will downsample the data 
                data_single.append(row)
        #light_data.append(data_single) #for more than one fly
        light_data = data_single    

    light_column = get_diode_column(light_data)
    #print(np.shape(light_column))

    # find peaks
    light_median = np.median(light_column)
    early_light_max = max(light_column[0:2000])
    light_peaks, properties = scipy.signal.find_peaks(light_column, height = early_light_max +.001, prominence = .1, distance = 10)
    #there is a condition that requires this, but I can't remember exactly what the data looked like
    if len(light_peaks) == 0:
        #print("There are no light peaks for " + str(date) + " " + str(fly))
        printlog("attempting new early_light_max, because no light peaks")
        early_light_max = max(light_column[0:100])
        light_peaks, properties = scipy.signal.find_peaks(light_column, height = early_light_max +.001, prominence = .1, distance = 10)
        
        if len(light_peaks) == 0:
            fly_name = Path.split('/')[0]
            printlog("There are still no light peaks after correction attempt for " + str(fly_name))
            printlog("skipping this fly--no light peaks")
            light_peaks = None ##this could be the case for control flies
            
    
    ## convert to seconds
    if light_peaks is not None:
        voltage_framerate =  10000/data_reducer #frames/s # 1frame/.1ms * 1000ms/1s = 10000f/s
        light_peaks_adjusted = light_peaks/voltage_framerate
    else:
        light_peaks_adjusted = None
        printlog("NO LIGHT PEAKS DATA")

    return light_peaks_adjusted


def find_moco_file(Path):
    """path should be fly folder. This returns the path to the moco ch2 h5 file"""
    for name in os.listdir(Path):
        if 'MOCO_ch2' in name:
            moco_file = name
            moco_path = os.path.join(Path, moco_file)
    return moco_path

def find_voltage_file(Path):
    """path should be fly folder. Returns path to specific voltage csv"""
    for name in os.listdir(Path):
        if 'Voltage' in name and '.csv' in name:
            voltage_file = name
            voltage_path = os.path.join(Path, voltage_file)
    return voltage_path


def add_to_h5(Path, key, value):
    """should be h5file as path.
    adds new key value to h5 file and checks if it already exists
    does overwrite"""
    with h5py.File(Path, 'a') as f:
        if key not in f.keys(): #check if key already in file
            #f[key] = value
            f.create_dataset(key, data = value)
        else:
            del f[key]
            #print('deleting old key and OVERWRITING')
            #f[key] = value
            f.create_dataset(key, data = value)
            
            
            
def run_PCA (Path, n_components, key = 'data'):
    """input path to h5 file. will default to do non-zscore data, but can specify another key (i.e. 'zscore'). 
    Returns loadings and components reshaped back to n_components, x, y, z"""
    
    t_batch = 200 #number of timepoints to run (this used to be 200, but I'm dropping to try to not get small batch errors?)
    minimum = 100
    with h5py.File(Path, 'r') as hf:  
        moco_data = hf[key]  
        dims = np.shape(moco_data) #x,y,z,t
    #     ##remove first 3 z slices
    #     moco_data = moco_data[:,:,3:,:] #to get rid of first 3 z slices
    #     dims = np.shape(moco_data)

        #run through batches of t so it can load in memory
        windows = np.arange(0,dims[-1], t_batch)
        transformer = IncrementalPCA(n_components = n_components)

        # for window_index in range(len(windows)):
        #     #find out if it is the last window OR if the last batch will be too small and have it go to the end
        #     if windows[window_index] == windows[-1] or dims[3] - windows[window_index] < t_batch + minimum: #last case go to end of dims (dims[-1])
        #         moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:dims[-1]])
        #         moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
        #         transformer.partial_fit(moco_data_reshaped)
        #     else:
        #         moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:windows[window_index + 1]])
        #         moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
        #         transformer.partial_fit(moco_data_reshaped)

        for window_index in range(len(windows)-1):
            #find out if it is the last window OR if the last batch will be too small and have it go to the end
            if windows[window_index] == windows[-2]: # or dims[3] - windows[window_index] < t_batch + minimum: #last case go to end of dims (dims[-1])
                moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:dims[-1]])
                moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                transformer.partial_fit(moco_data_reshaped)
            elif windows[window_index] == windows[-1]:  #just skip the last one because second to last should do both
                printlog(f'last batch size = {dims[3] - windows[window_index]}')
            else:
                moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:windows[window_index + 1]])
                moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                transformer.partial_fit(moco_data_reshaped)

        components = transformer.components_  #ndarray of shape (n_components, n_features)
        #reshape back components to xyz
        reshaped_components = np.reshape(components, (n_components,) + dims[0:3]) #components, x,y,z
        
        ###plotting components DOES NOT CURRENTLY GET RETURNED (easy to do later)
        #components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(reshaped_components.shape[3])], axis=2)

        ##run through data again to get time relevant information
        all_loadings = []
        for window_index in range(len(windows)):
            if windows[window_index] == windows[-1]: #last case go to end of dims (dims[-1])
                moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:dims[-1]])
                moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                all_loadings.append(transformer.transform(moco_data_reshaped))
            else:
                moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:windows[window_index + 1]])
                moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                all_loadings.append(transformer.transform(moco_data_reshaped))
        loadings = np.concatenate(all_loadings, 0)
        
        return loadings, reshaped_components

def get_fly_name_from_path (Path):
    """will get last folder in path (assumes fly name is the last folder)"""
    fly_name = Path.split('/')[-1]
    return fly_name

def get_Bruker_framerate(Path, z_number = 49):
    """from path will return framerate using xml file to calculate. 
    z can be specified, but its just used to get to midpoint of stack. 
    If the stack is less than the specified z this will fail. in future have it revert to z = 1"""
    fly_name = get_fly_name_from_path(Path)
    xml_file = str(fly_name) + '.xml'
    timestamps = load_timestamps(Path, xml_file)
    
    z = int(z_number/2) #to get roughly middle z

    z_timestamps = []
    for t_slice in timestamps:
        z_timestamps.append(t_slice[z])

    z_timestamps = np.array(z_timestamps)
    z_time_mean = np.mean(z_timestamps[1:] - z_timestamps[:-1])
    bruker_framerate = 1000/z_time_mean #f/s
    z_timestamps_s = z_timestamps/1000
    
    return bruker_framerate
    
def run_STA (Path, loading):
    """path to folder, this will generate xml file. will also calculate light peaks adjusted. This works for single loading.
    returns a list with loading values seperated by light as different trials"""
    bruker_framerate = get_Bruker_framerate(Path)
    light_peaks_adjusted = get_light_peaks(Path)
    
    all_trials = []
    for light_index in range(len(light_peaks_adjusted)): #look at each time
        if light_index != 0: ##I don't want the data before the first light flash
            current_light = light_peaks_adjusted[light_index]
            previous_light = light_peaks_adjusted[light_index - 1]
            current_index = math.floor(current_light/bruker_framerate) #round down
            prev_index = math.ceil(previous_light/bruker_framerate)  #round up
            trial = loading[prev_index:current_index]
            all_trials.append(trial)
            
    return all_trials


if __name__=='__main__':
    main(json.loads(sys.argv[1]))
            