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







 





         
            
            
def run_PCA (h5file, n_components, key = 'data'):
    """input path to h5 file. will default to do non-zscore data, but can specify another key (i.e. 'zscore').
    Data needs to be in [x,y,z,t] format 
    Returns loadings and components reshaped back to n_components, x, y, z"""
    
    t_batch = 200 #number of timepoints to run (this used to be 200, but I'm dropping to try to not get small batch errors?)
    minimum = 100
    with h5py.File(h5file, 'r') as hf:  
        nan_data = hf[key]  ##this data has nans probably
        dims = np.shape(nan_data) #x,y,z,t
    #     ##remove first 3 z slices
    #     moco_data = moco_data[:,:,3:,:] #to get rid of first 3 z slices
        data = np.nan_to_num(nan_data)

        #run through batches of t so it can load in memory
        windows = np.arange(0,dims[-1], t_batch)
        transformer = IncrementalPCA(n_components = n_components)


        for window_index in range(len(windows)-1):
            #find out if it is the last window OR if the last batch will be too small and have it go to the end
            if windows[window_index] == windows[-2]: # or dims[3] - windows[window_index] < t_batch + minimum: #last case go to end of dims (dims[-1])
                data_subset = np.array(data[:,:,:, windows[window_index]:dims[-1]])
                data_reshaped = np.reshape(data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                transformer.partial_fit(data_reshaped)
            elif windows[window_index] == windows[-1]:  #just skip the last one because second to last should do both
                print(f'last batch size = {dims[3] - windows[window_index]}')
            else:
                data_subset = np.array(data[:,:,:, windows[window_index]:windows[window_index + 1]])
                data_reshaped = np.reshape(data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                transformer.partial_fit(data_reshaped)

        components = transformer.components_  #ndarray of shape (n_components, n_features)
        #reshape back components to xyz
        reshaped_components = np.reshape(components, (n_components,) + dims[0:3]) #components, x,y,z
        
        ###plotting components DOES NOT CURRENTLY GET RETURNED (easy to do later)
        #components_shape_plotting = np.concatenate([reshaped_components[:, :, :, i] for i in range(reshaped_components.shape[3])], axis=2)

        ##run through data again to get time relevant information
        all_loadings = []
        for window_index in range(len(windows)):
            if windows[window_index] == windows[-1]: #last case go to end of dims (dims[-1])
                data_subset = np.array(data[:,:,:, windows[window_index]:dims[-1]])
                data_reshaped = np.reshape(data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                all_loadings.append(transformer.transform(data_reshaped))
            else:
                data_subset = np.array(data[:,:,:, windows[window_index]:windows[window_index + 1]])
                data_reshaped = np.reshape(data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                all_loadings.append(transformer.transform(data_reshaped))
        loadings = np.concatenate(all_loadings, 0)
        
        return loadings, reshaped_components




     




            


def get_brain_t_switch_set(dataset_path, exp_length1 = 20, exp_length2 = 40, roi_peaks = False):
    """returns array of arrays of switch times that correspond to index in t of brains.
    returns seperately 20 and 40s experiemnts
    20s_t_points = [[start1 stop1] [start 2 stop2]]
    *takes time from zstack timestamps to find which zstack the light is in"""
    
    light_peaks_twenty_times, light_peaks_forty_times = get_times_switch_blocks (dataset_path, exp_length1, exp_length2, roi_peaks = roi_peaks)
    timestamps = load_timestamps(dataset_path)
    average_timestamps = np.mean(timestamps, axis = 1)/1000  ##to convert ms to s to match light_peaks
    
    first_timestamps = []
    last_timestamps = []
    for t in timestamps:
        first_timestamps.append(t[0])
        last_timestamps.append(t[-1])

    first_timestamps = np.array(first_timestamps)
    first_timestamps_s = first_timestamps/1000
    last_timestamps = np.array(last_timestamps)
    last_timestamps_s = last_timestamps/1000
    
    twenty_switch_set_t = []
    forty_switch_set_t = []
    for switch_set in light_peaks_twenty_times:
        start_time = switch_set[0]
        end_time = switch_set[1]
        
        ##find start time based on z-stack times
        #the last z = 0 timstamp that is less then switch time
        first_index_start = np.where(first_timestamps_s < start_time)[0][-1]
        #last z slice (z = 49) that switch time happens before
        last_index_start = np.where(last_timestamps_s > start_time)[0][0]
        if first_index_start == last_index_start:
            start_time_index = first_index_start
        ##find out if it's in the middle of two stacks
        elif last_timestamps_s[first_index_start] < start_time < first_timestamps_s[last_index_start]:
            ##then it's between timestamps, if start time then have switch start at the following zstack
            start_time_index = last_index_start
        else:
            #this shouldn't happen
            print('odd scenario. not in same z-stack and not between z-stacks')
            
        #end time
        first_index_end = np.where(first_timestamps_s < end_time)[0][-1]
        last_index_end = np.where(last_timestamps_s > end_time)[0][0]
        if first_index_end == last_index_end:
            end_time_index = first_index_end
        elif last_timestamps_s[first_index_end] < end_time < first_timestamps_s[last_index_end]:
            #ending index choose the zstack before (miss the bit between, but I'm removing that data anyway)
            end_time_index = first_index_end
        else:
            #this shouldn't happen
            print('odd scenario. not in same z-stack and not between z-stacks')

        both = (start_time_index, end_time_index)
        twenty_switch_set_t.append(both)

    for switch_set in light_peaks_forty_times:
        start_time = switch_set[0]
        end_time = switch_set[1]
        
        ##find start time based on z-stack times
        #the last z = 0 timstamp that is less then switch time
        first_index_start = np.where(first_timestamps_s < start_time)[0][-1]
        #last z slice (z = 49) that switch time happens before
        last_index_start = np.where(last_timestamps_s > start_time)[0][0]
        if first_index_start == last_index_start:
            start_time_index = first_index_start
        ##find out if it's in the middle of two stacks
        elif last_timestamps_s[first_index_start] < start_time < first_timestamps_s[last_index_start]:
            ##then it's between timestamps, if start time then have switch start at the following zstack
            start_time_index = last_index_start
        else:
            #this shouldn't happen
            print('odd scenario. not in same z-stack and not between z-stacks')
            
        #end time
        first_index_end = np.where(first_timestamps_s < end_time)[0][-1]
        last_index_end = np.where(last_timestamps_s > end_time)[0][0]
        if first_index_end == last_index_end:
            end_time_index = first_index_end
        elif last_timestamps_s[first_index_end] < end_time < first_timestamps_s[last_index_end]:
            #ending index choose the zstack before (miss the bit between, but I'm removing that data anyway)
            #changin this to last index because it's been ending too early
            end_time_index = last_index_end
        else:
            #this shouldn't happen
            print('odd scenario. not in same z-stack and not between z-stacks')

        both = (start_time_index, end_time_index)
        forty_switch_set_t.append(both)
    twenty_switch_set_t = np.array(twenty_switch_set_t)
    forty_switch_set_t = np.array(forty_switch_set_t)
    return twenty_switch_set_t, forty_switch_set_t

def get_times_switch_blocks (dataset_path, exp_length1 = 20, exp_length2 = 40, roi_peaks = False):
    """returns array of arrays of times in s that each block 
    starts and ends seperate arrays returned for 20 and 40 (or specified expt times)
    i.e. 20s_times = [[30.9 400.2][600.7  987.6]]  [[start1 stop 1] [start 2 stop 2]] """
    
    ##getting light peaks in this function is unnececessary
    if roi_peaks == False:
        light_peaks_path = os.path.join(dataset_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        if opened_peaks is not None:
            light_peaks = opened_peaks/1000
            print('found light in h5 file')
        else:
            light_peaks = get_light_peaks(dataset_path)/1000
    else:
        print('opening light from roi')
        light_peaks = get_roi_light_peaks(dataset_path)

    twenty, forty = get_switch_start_stop_indices(dataset_path, exp_length1, exp_length2, roi_peaks = roi_peaks)
    
    light_peaks_twenty_times = []
    for set_index in range(len(twenty)):
        t = (light_peaks[twenty[set_index][0]], light_peaks[twenty[set_index][1]])
        light_peaks_twenty_times.append(t)

    light_peaks_forty_times = []
    for set_index in range(len(forty)):
        t = (light_peaks[forty[set_index][0]], light_peaks[forty[set_index][1]])
        light_peaks_forty_times.append(t)

    light_peaks_twenty_times = np.array(light_peaks_twenty_times)
    light_peaks_forty_times = np.array(light_peaks_forty_times)
    
    return light_peaks_twenty_times, light_peaks_forty_times


##support functions
def get_switch_start_stop_indices(dataset_path, exp_length1 = 20, exp_length2 = 40, roi_peaks = False):
    """returns an array of tuples of start and stop indices for starts and stops of 20s or 40s. 
    20 and 40 are returned in seperate arrays.
    inclusive (start = first index and stop = last index)"""
    switch_points = find_switch_points(dataset_path, roi_peaks = roi_peaks)
    if roi_peaks == False:
        light_peaks_path = os.path.join(dataset_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        if opened_peaks is not None:
            light_peaks = opened_peaks/1000
        else:
            light_peaks = get_light_peaks(dataset_path)/1000
    else:
        print('opening light from roi')
        light_peaks = get_roi_light_peaks(dataset_path)
    
    light_times = light_peaks[1:]- light_peaks[0:-1]
    twenty = []
    forty = []
    for i in range(len(switch_points)):
        switch_index = switch_points[i] 
        print(switch_index)
        print(light_times[switch_index])
        if i == 0:
            if exp_length1 - 5 < light_times[switch_index] < exp_length1 + 5:
                t = (0, switch_index + 1) #the + 1 helps it end and start at the same place
                twenty.append(t)
            elif exp_length2 - 5 < light_times[switch_index] < exp_length2 + 5:
                t = (0, switch_index + 1)
                forty.append(t)
        else:
            previous_index = switch_points[i - 1] + 1 
            if exp_length1 - 5 < light_times[switch_index] < exp_length1 + 5:
                t = (previous_index, switch_index + 1)
                twenty.append(t)
            elif exp_length2 - 5 < light_times[switch_index] < exp_length2 + 5:
                t = (previous_index, switch_index + 1)
                forty.append(t)
    twenty = np.array(twenty)
    forty = np.array(forty)
    return twenty, forty


def find_switch_points(dataset_path, difference=15, roi_peaks = False):
    """takes dataset path and imports light peaks and returns the times there is a switch
    args:
    dataset_path = path to fly folder that has voltage file
    difference = value that it will sort by to see if there is a switch point. 
    The difference between two intervals should be greater than this number (i.e. 40-20 = 20 >15)
    returns:
    indices of the last trial before switch"""
    
    #get light peaks
    if roi_peaks == False:
        light_peaks_path = os.path.join(dataset_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        print(opened_peaks)
        if opened_peaks is not None:
            light_peaks = opened_peaks/1000
        else:
            light_peaks = get_light_peaks(dataset_path)/1000
    else:
        print('opening light from roi')
        light_peaks = get_roi_light_peaks(dataset_path)

    #find times between light flashes
    light_times = light_peaks[1:]- light_peaks[0:-1] 
    #check that light peaks is single light peaks 
    if len(np.where(light_times < difference)[0]):
        #light_peaks is taking more than one datapoint per peak
        raise Exception(f'WARNING: these are not single peaks check indices {np.where(light_times<15)[0]}')
    
    #find switch points
    light_times_diff = np.rint(abs(light_times[1:] - light_times[0:-1]))
    switch_ind = np.where(light_times_diff > 15)[0] 
    #switch_ind = np.insert(switch_ind, 0,light_times_diff[0]) #This will add 0 but I don't need it
     
#     ##switch times in s
#     switch_times_s = light_peaks[switch_ind]
    
#     #block interval values
#     #skip 0 because it is dark and then subtract 1 to make sure its in the block 
#     #(the end point is the last point anyway so it should be fine without the -1)
#     ind_to_get_ints = switch_ind[1:] - 1 
#     interval_sets = light_times[ind_to_get_ints]
#     interval_sets_int = [int(i) for i in interval_sets]
    
    return switch_ind

## get light peaks
## functions
## get data out of voltage file     
#get just diode column
# def get_diode_column(raw_light_data): this version does not work for data that has 3 columns
#     """light data should be single fly and have the header be the first row"""
#     header = raw_light_data[0]
#     diode_column = []
#     for i in range(len(header)):
#         #if 'diode' in header[i]:
#         if 'Input 0' in header[i]: #for new split straagey
#             diode_column = i
#     reshape_light_data = np.transpose(raw_light_data[1:])
#     column = reshape_light_data[:][diode_column] #don't want header anymore
#     column = [float(i) for i in column] #for some reason it was saved as string before
#     return column

def get_diode_column(raw_light_data):
    #this one
    """light data should be single fly and have the header be the first row"""
    header = raw_light_data[0]
    diode_column = []
    for i in range(len(header)):
        #if 'diode' in header[i]:
        if 'Input 0' in header[i]: #for new split straagey
            diode_column = i
            print(f'found diode column {i}')
    #reshape_light_data = np.transpose(raw_light_data[1:])
    column = []
    for row in raw_light_data[1:-1]:  ##sometimes getting errors with last row
        column.append(float(row[diode_column]))  #added [1:] because was trying to add header
    return column


## get xml timestamps
def load_timestamps(directory, fix = False):
    """ Parses a Bruker xml file to get the times of each frame, or loads h5py file if it exists.
    First tries to load from 'timestamps.h5' (h5py file). If this file doesn't exist
    it will load and parse the Bruker xml file, and save the h5py file for quick loading in the future.
    updaate: now have two timestamp functions find_timestamps() will generate timestamps without looking up

    Parameters
    ----------
    directory: full directory that contains xml file (str). (fly_path)
    
    Returns
    -------
    timestamps: [t,z] numpy array of times (in ms) of Bruker imaging frames.
    """
    try:
        print('Trying to load timestamp data from hdf5 file.')
        with h5py.File(os.path.join(directory, 'timestamps.h5'), 'r') as hf:
                timestamps = hf['timestamps'][:]
    except:
        print(f'RUNNING FIND TIMESTAMPS and RESAVING. fix = {fix}')
        timestamps = find_timestamps(directory, fix = fix)
    return timestamps

    # try:
    #     print('Trying to load timestamp data from hdf5 file.')
    #     with h5py.File(os.path.join(directory, 'timestamps.h5'), 'r') as hf:
    #         timestamps = hf['timestamps'][:]
    
    # except:
    #     fly_name = get_fly_name_from_path(directory)
    #     file = str(fly_name) + '.xml'
    #     print('Failed. Extracting frame timestamps from bruker xml file.')
    #     xml_file = os.path.join(directory, file)
    #     print(f'getting timestamps from {xml_file}')
    #     tree = ET.parse(xml_file)
    #     root = tree.getroot()
    #     timestamps = []

    #     sequences = root.findall('Sequence')
    #     first_frame_len = len(sequences[0].findall('Frame'))
    #     for sequence_i in range(len(sequences)):
    #         sequence = sequences[sequence_i]
    #         frames = sequence.findall('Frame')
    #         #skip remaining sequences if ended early
    #         if len(frames) != first_frame_len:
    #             print(f'sequence # {sequence_i} did not complete z-series => ending')
    #             sequence_length = sequence_i #want it to be length to previous sequence value since that was the last complete one => 0 indexing helps
    #         else:
    #             for frame in frames:
    #                 filename = frame.findall('File')[0].get('filename')
    #                 time = float(frame.get('relativeTime'))
    #                 timestamps.append(time)
    #             sequence_length = len(sequences)
    #     timestamps = np.multiply(timestamps, 1000)

    #     if len(sequences) > 1:
    #         timestamps = np.reshape(timestamps, (sequence_length, first_frame_len))
    #     else:
    #         timestamps = np.reshape(timestamps, (first_frame_len, sequence_length))
    # if fix == False:
    #     ### Save h5py file ###
    #     with h5py.File(os.path.join(directory, 'timestamps.h5'), 'w') as hf:
    #         hf.create_dataset("timestamps", data=timestamps)
            
    #         print('Success.')
    #         return timestamps
    # elif fix == True: ## this means that need to delete timestamps due to split_nii error
    #     new_timestamps = []
    #     for t in range(len(timestamps)):
    #         #timestamps to keep
    #         if (t + 1) % skip_number != 0:
    #             new_timestamps.append(timestamps[t])
    #     new_timestamps = np.array(new_timestamps)
    #     with h5py.File(os.path.join(directory, 'timestamps.h5'), 'w') as hf:
    #         hf.create_dataset("timestamps", data=new_timestamps)
    #         print('Success.')
    #         return new_timestamps
        
## get xml timestamps
def find_timestamps(directory, fix = False):
    """ Parses a Bruker xml file to get the times of each frame. 
    it will load and parse the Bruker xml file, and save the h5py file for quick loading in the future.
    Parameters
    ----------
    directory: full directory that contains xml file (str).
    fix: bool that if true deletes timestamps corresponding to deleted timestamps in tiff_split_nii
    determines if it should delete every 500 or every 1000 timepoints based on the split nii files in the directory
    
    Returns
    -------
    timestamps: [t,z] numpy array of times (in ms) of Bruker imaging frames.
    """

    fly_name = get_fly_name_from_path(directory)
    file = str(fly_name) + '.xml'
    print('Extracting frame timestamps from bruker xml file.')
    xml_file = os.path.join(directory, file)
    print(f'getting timestamps from {xml_file}')
    tree = ET.parse(xml_file)
    root = tree.getroot()
    timestamps = []

    sequences = root.findall('Sequence')
    first_frame_len = len(sequences[0].findall('Frame'))
    for sequence_i in range(len(sequences)):
        sequence = sequences[sequence_i]
        frames = sequence.findall('Frame')
        #skip remaining sequences if ended early
        if len(frames) != first_frame_len:
            print(f'sequence # {sequence_i} did not complete z-series => ending')
            sequence_length = sequence_i #want it to be length to previous sequence value since that was the last complete one => 0 indexing helps
        else:
            for frame in frames:
                filename = frame.findall('File')[0].get('filename')
                time = float(frame.get('relativeTime'))
                timestamps.append(time)
            sequence_length = len(sequences)
    timestamps = np.multiply(timestamps, 1000)

    if len(sequences) > 1:
        timestamps = np.reshape(timestamps, (sequence_length, first_frame_len))
    else:
        timestamps = np.reshape(timestamps, (first_frame_len, sequence_length))
    if fix == False:
        ### Save h5py file ###
        with h5py.File(os.path.join(directory, 'timestamps.h5'), 'w') as hf:
            hf.create_dataset("timestamps", data=timestamps)
            print('Success.')
            return timestamps
        
    elif fix == True: ## this means that need to delete timestamps due to split_nii error
        drop_number = get_timestamp_drop_number(directory)
        new_timestamps = []
        for t in range(len(timestamps)):
            #timestamps to keep
            if (t + 1) % drop_number != 0:
                new_timestamps.append(timestamps[t])
        new_timestamps = np.array(new_timestamps)
        with h5py.File(os.path.join(directory, 'timestamps.h5'), 'w') as hf:
            hf.create_dataset("timestamps", data=new_timestamps)
            print('Success--saved fixed (new) timestamps')
            return new_timestamps
        

def get_timestamp_drop_number (directory):
    """looks in the fly directory for split nii files to see if timepoints were dropped every 500 frames or every 1000
    directory = fly_path that has split nii files
    returns 500 or 1000"""
    files = os.listdir(directory)
    identifier = "channel_1_s500.nii"
    pos_control = "channel_1_s1000.nii"
    split_500 = []
    control = []
    for file in files:
        if identifier in file:
            split_500.append(file)
        if pos_control in file:
            control.append(file)
    #see if 500 file exists (if so then it dropped every 500 timepoint)
    if len(split_500) > 0 and len(control) > 0:
        return 500
    elif len(split_500) == 0 and len(control)> 0:
        return 1000
    else:
        fly = directory.split("/")[-1]
        raise Exception(f'could not find split files for fly {fly}')
        
            


def get_light_peaks_brain_time(fly_path, max_dims, light_buffer_ms = 100, roi_peaks = False):
    """gets light peaks in terms of brain time index.
    Note: this may end up being longer than light_peaks_ms because 
    if the light turns on between two zstacks it records the closer 
    one or records both if they are both < 100ms from the flash.
    max dims is the t dims of the brain (sometimes voltage recording extends longer than 2p imaging)"""
    
    if roi_peaks == False:
        light_peaks_path = os.path.join(fly_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        if opened_peaks is not None:
            light_peaks_s = opened_peaks/1000
        else:
            light_peaks_s = get_light_peaks(fly_path)/1000
    else:
        print('opening light from roi')
        light_peaks_s = get_roi_light_peaks(fly_path)
    timestamps = load_timestamps(fly_path)
    #average_timestamps = np.mean(timestamps, axis = 1)/1000  ##to convert ms to s to match light_peaks

#     light_buffer_ms = 100 #the number of ms that the peak light flash needs to be away from the start or end of zstack to not elimiante the data
    first_timestamps = []
    last_timestamps = []
    for t in timestamps:
        first_timestamps.append(t[0])
        last_timestamps.append(t[-1])
        
    first_timestamps = np.array(first_timestamps)
    first_timestamps_s = first_timestamps/1000
    last_timestamps = np.array(last_timestamps)
    last_timestamps_s = last_timestamps/1000
    
    light_peaks_t = []
    for light in light_peaks_s:
        if light < last_timestamps_s[-1]: #sometimes roi light continues beyond imaging experiment
            last = np.where(last_timestamps_s >= light)[0][0]
            first = np.where(first_timestamps_s <= light)[0][-1]
            ##check to make sure it is within brain time
            if last <= max_dims:
                #then sort out which ones to append based on when the light is coming on in relation to brain volume
                if last == first:
                    light_peaks_t.append(last) #since the are the same then the light is in this zstack
                    
                    #extra
                    light_peaks_t.append(last-1)
                    light_peaks_t.append(last +1)
                    
                elif last != first: #then the light comes on between two zstacks
                    #determine which one it is closer to.
                    time_start_last = first_timestamps_s[last] #the start of the zstack that happens just after flash
                    time_end_first = last_timestamps_s[first] #the end of the zstack that happens just before the flash

                    if time_start_last - light  < light - time_end_first:
                        #then the flash is closer to the "last" index
            #             print('closer to second stack')
            #             print('diff ms = ', (time_start_last - light)*1000)
                        light_peaks_t.append(last)
                        
                        #extra
                        light_peaks_t.append(last - 1)
                        light_peaks_t.append(last +1)
                        
                        #check if it is very close to the last index too though
                        if (light - time_end_first)*1000 < light_buffer_ms:
                            light_peaks_t.append(first) #if it's close then add the other zstack to be removed too

                    else:
                        #light is closet to the "first" index
            #             print('closer to first stack')
            #             print('diff ms = ', (light - time_end_first)*1000)
                        light_peaks_t.append(first)
                
                        #extra
                        light_peaks_t.append(first - 1)
                        light_peaks_t.append(first +1)
                        
                        #check if it is very close to the last index too though
                        if (time_start_last - light)*1000 < light_buffer_ms:
                            light_peaks_t.append(last) #if it's close then add the other zstack to be removed too
    return light_peaks_t


def get_light_peaks_brain_t_no_bleedthrough (fly_path, roi_peaks = False):
    """same as get_light_peaks_brain_t except it removes the added stacks to add as a buffer 
    so it only removes the stack that have a light in them. If it's between stacks it will find the stack the light is closest to.
    consider if this will be an issue. I think not since I remove data that clsoe to the light.
    Need to make sure the data removal isn't an issue too"""
    if roi_peaks == False:
        light_peaks_path = os.path.join(fly_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        if opened_peaks is not None:
            light_peaks_s = opened_peaks/1000
        else:
            light_peaks_s = get_light_peaks(fly_path)/1000
    else:
        print('opening light from roi')
        light_peaks_s = get_roi_light_peaks(fly_path)

    timestamps = load_timestamps(fly_path)
    print(np.shape(timestamps))
    #average_timestamps = np.mean(timestamps, axis = 1)/1000  ##to convert ms to s to match light_peaks

    #     light_buffer_ms = 100 #the number of ms that the peak light flash needs to be away from the start or end of zstack to not elimiante the data
    first_timestamps = []
    last_timestamps = []
    for t in timestamps:
        first_timestamps.append(t[0]) #time at the first z position
        last_timestamps.append(t[-1]) #time at the last z position

    first_timestamps = np.array(first_timestamps)
    first_timestamps_s = first_timestamps/1000
    last_timestamps = np.array(last_timestamps)
    last_timestamps_s = last_timestamps/1000

    light_peaks_t = []
    for light in light_peaks_s:
        if light < last_timestamps_s[-1]: #sometimes roi light continues beyond imaging experiment
            last = np.where(last_timestamps_s >= light)[0][0]  #the stack num where the light time is less than the last z time in the stack
            first = np.where(first_timestamps_s <= light)[0][-1] # the stack num where the light time is greater tahn the first z time in the stack
            #ort out which ones to append based on when the light is coming on in relation to brain volume
            if last == first:
                light_peaks_t.append(last) #since the are the same then the light is in this zstack
            elif last != first: #then the light comes on between two zstacks
                #determine which one it is closer to.
                time_start_last = first_timestamps_s[last] #the start of the zstack that happens just after flash
                time_end_first = last_timestamps_s[first] #the end of the zstack that happens just before the flash

                if time_start_last - light  < light - time_end_first:
                    #then the flash is closer to the "last" index
                    light_peaks_t.append(last)
                else:
                    #light is closet to the "first" index
                    light_peaks_t.append(first)
    return light_peaks_t


def get_voltage_data(dataset_path):
    """gets voltage data from voltage file and 
    returns a list of times and a list of voltage values.
    
    args:
    Path = path to fly (folder that contains brain data and voltage data)
    data_reducer = default 100, to reduce the number of timepoints 
    it gets because the resolution is very high when collected
    
    returns:
    voltage data: list of voltage values (every data reducer amount)
    voltage_time: list of timepoints saved by voltage file"""
    
    #1. get voltage file
    #2. get time column (first column)
    #3. get data column 
    voltage_path = find_voltage_file(dataset_path)
    with open(voltage_path, 'r') as rawfile:
        reader = csv.reader(rawfile)
        data_single = []
#         for i, row in enumerate(reader):
#             if i % data_reducer == 0: #will downsample the data 
#                 data_single.append(row)
        for i, row in enumerate(reader):
            data_single.append(row)
        light_data = data_single    

    light_data_column = get_diode_column(light_data)
    time_data_column = get_time_column(light_data)
    return light_data_column, time_data_column
    
def get_time_column(raw_light_data):
    """light data should be single fly and have the header be the first row"""
    header = raw_light_data[0]
    diode_column = []
    for i in range(len(header)):
        if 'Time(ms)' in header[i]: 
            time_column = i
            print(f'found time column {i}')
#         else:
#             print(f'could not find "Time(ms)" in header{header}')
    #reshape_light_data = np.transpose(raw_light_data[1:])
    column = []
    for row in raw_light_data[1:-1]: #sometimes last row is bad
        column.append(float(row[time_column])) #adding [1:] to be consistent with diode column
    return column


def get_light_peaks (dataset_path): #, data_reducer = 100):
    
    """input fly path and get out the light peaks files in milliseconds"""

    voltage_multiplier = 1 ##20231102 no longer need correction. Sorted out issue was from indexing and dropping timepoints in split nii
    light_data_column, time_data = get_voltage_data(dataset_path)

    # find peaks
    light_median = np.median(light_data_column)
    early_light_max = max(light_data_column[0:2000])
    light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max +.001, prominence = .1, distance = 10)
    #there is a condition that requires this, but I can't remember exactly what the data looked like
    if len(light_peaks) == 0:
        print("attempting new early_light_max, because no light peaks")
        early_light_max = max(light_data_column[0:100])
        #light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max +.001, prominence = .1, distance = 10)
        light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max*0.6, prominence = .1, distance = 10)
        if len(light_peaks) == 0:
            print("There are still no light peaks, attempting without prominence")
            early_light_max = max(light_data_column[0:2000])
            light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max*0.6, distance = 10)
            print(f'early light max 0:2000 {early_light_max}')
            if len(light_peaks) == 0:
                print("skipping this fly--no light peaks")
            
    
#     ## convert to seconds
#     voltage_framerate =  10000/data_reducer #frames/s # 1frame/.1ms * 1000ms/1s = 10000f/s
#     light_peaks_adjusted = light_peaks/voltage_framerate
    
    ##use time to give voltage in time
    ##light_peaks should be the indices of peaks => I can check the indices in time column
    light_peaks = np.array(light_peaks)
    print(np.shape(light_peaks))
    time_data = np.array(time_data)
    light_ms = time_data[light_peaks]*voltage_multiplier

    #save light peaks
    light_peaks_path = os.path.join(dataset_path, 'light_peaks.h5')
    #add_to_h5(light_peaks_path, 'light peaks ms', light_ms)
    
    #get just one peak (will take the last value before the drop)
    single_light_ms = get_single_light_peaks(light_ms, 10000)
    add_to_h5(light_peaks_path, 'light peaks ms', single_light_ms)
    return single_light_ms




def get_single_light_peaks(light_peaks, seperator):
    """takes in array of light peaks and makes sure they are at least seperator distance apart
    args:
    light_peaks = array that has the peaks in it (in ms or s but change seperator)
    seperator = value that two adjacent peaks must be apart in order to be kept. 
    last number that is far enough apart will be kept"""
    diff = light_peaks[1:] - light_peaks[0:-1]
    single_light_peak_indices = np.where(diff>seperator)[0]
    single_light_peaks = light_peaks[single_light_peak_indices]
    return single_light_peaks
#     single_light_peaks = []
#     for i in range(len(light_peaks)-1):
#         current = light_peaks[i]
#         next_time = light_peaks[i+1]
#         if next_time - current > seperator:
#             single_light_peaks.append(current)
#     single_light_peaks = np.array(single_light_peaks)
#     return single_light_peaks


def find_moco_file(dataset_path):
    """path should be fly folder. This returns the path to the moco ch2 h5 file"""
    for name in os.listdir(dataset_path):
        if 'MOCO_ch2' in name:
            moco_file = name
            moco_path = os.path.join(dataset_path, moco_file)
    return moco_path

def find_voltage_file(dataset_path):
    """path should be fly folder. Returns path to specific voltage csv"""
    for name in os.listdir(dataset_path):
        if 'Voltage' in name and '.csv' in name:
            voltage_file = name
            voltage_path = os.path.join(dataset_path, voltage_file)
    return voltage_path


def add_to_h5(dataset_path, key, value):
    """adds new key value to h5 file and checks if it already exists
    does overwrite"""
    with h5py.File(dataset_path, 'a') as f:
        if key not in f.keys(): #check if key already in file
            f[key] = value
        else:
            del f[key]
            #print('deleting old key and OVERWRITING')
            f[key] = value
            
            
def open_light_peaks(savepath):
    if os.path.exists(savepath):
        with h5py.File(savepath, 'a') as f:
            if 'light peaks ms' in f.keys():
                print('found "light peaks ms" key! returning light peaks')
                return f['light peaks ms'][()]
            else: 
                print(f'Could not find "light peaks ms" key so returning "None"')
                return None
    else:
        print(f'light peaks path {savepath} does not exist') 
        return None           


def get_fly_name_from_path (dataset_path):
    """will get last folder in path (assumes fly name is the last folder)"""
    fly_name = dataset_path.split('/')[-1]
    return fly_name

def get_Bruker_framerate(dataset_path, z_number = 49):
    """from path will return framerate using xml file to calculate. 
    z can be specified, but its just used to get to midpoint of stack. 
    If the stack is less than the specified z this will fail. in future have it revert to z = 1"""
    fly_name = get_fly_name_from_path(dataset_path)
    xml_file = str(fly_name) + '.xml'
    timestamps = load_timestamps(dataset_path, xml_file)
    
    #I can get z_number from second dim of timestamps
    z = int(z_number/2) #to get roughly middle z

    z_timestamps = []
    for t_slice in timestamps[0:400]:  #changing this to account for issues with deleted timepoints
        z_timestamps.append(t_slice[z])

    z_timestamps = np.array(z_timestamps)
    z_time_mean = np.mean(z_timestamps[1:] - z_timestamps[:-1])
    bruker_framerate = 1000/z_time_mean #f/s
    z_timestamps_s = z_timestamps/1000    
    return bruker_framerate
    
def run_STA (dataset_path, loading, roi_peaks = False):
    """path to folder, this will generate xml file. will also calculate light peaks adjusted. This works for single loading.
    returns a list with loading values seperated by light as different trials"""
    bruker_framerate = get_Bruker_framerate(dataset_path)
    if roi_peaks == False:
        light_peaks_path = os.path.join(dataset_path, 'light_peaks.h5')
        opened_peaks = open_light_peaks(light_peaks_path)
        if opened_peaks is not None:
            light_peaks_adjusted = opened_peaks/1000
        else:
            light_peaks_adjusted = get_light_peaks(dataset_path)/1000
    else:
        print('opening light from roi')
        light_peaks_adjusted = get_roi_light_peaks(dataset_path)
    
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


def make_meanbrain (steps, data):
        """takes steps (range start, stop, stepsize) and data = brain and returns meanbrain
        can be partial section--specify with steps"""
        sumbrain = 0
        total_timepoints = steps[-1] - steps[0]
        for chunk_num in range(len(steps)-1):
            chunk_start = steps[chunk_num]
            chunk_end = steps[chunk_num + 1]
            chunk = data[:,:,:,chunk_start:chunk_end]
            sumbrain += np.sum(chunk, axis = 3, keepdims = True)
        meanbrain = sumbrain/total_timepoints
        return meanbrain
    
    
def make_stdbrain (meanbrain, steps, data):
    """takes steps (range start, stop, stepsize) and data = brain and returns std of brain
        can be partial section--specify with steps"""
    total = 0
    total_timepoints = steps[-1] - steps[0]
    for chunk_num in range(len(steps) - 1):  
        chunk_start = steps[chunk_num]
        chunk_end = steps[chunk_num + 1]
        chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
        s = np.sum((chunk - meanbrain)**2, axis = 3, keepdims = True) #changed to sum of chunk
        total = s + total
    final_std = np.sqrt(total/total_timepoints) #fix this from len
    return final_std

def make_empty_h5(savefile, key, dims):
    """make empty h5 file with specified key and dims as the shape. returns the filename"""
    with h5py.File(savefile, 'w') as f:
        dset = f.create_dataset(key, dims, dtype='float32', chunks=True)
    return savefile
    

def get_video_framerate (cam_data_path):
    """input filepath to cam file from video file, will check both computer and 
    camera timestamps to verify that the framerate is similar and return cam fr"""
    allowed_variability = .1
    frames_to_use = 20000
    #get data
    num_list = []
    with open(cam_data_path, 'r') as fh:
        for line in fh:
            num_list.append((line.split()))
    #check first input
    single_column = []
    specified_column = 1
    for row in num_list:
        single_column.append(float(row[specified_column]))
    single_column = np.squeeze(np.array(single_column))
    #difference = single_column[1:] - single_column[0:-1]
    difference = single_column[100:frames_to_use] - single_column[99:frames_to_use-1]
    first_mean = np.mean(difference)*1000
    #check second input
    single_column = []
    specified_column = 2
    for row in num_list:
        single_column.append(float(row[specified_column]))
    single_column = np.squeeze(np.array(single_column))
    #difference = single_column[1:] - single_column[0:-1]
    difference = single_column[100:frames_to_use] - single_column[99:frames_to_use-1]

    second_mean = np.mean(difference)*1000
    
    #compare
    if abs(first_mean - second_mean) < allowed_variability:
        print(f'within {allowed_variability} \n mean difference = abs{first_mean - second_mean}, first = {first_mean}, second = {second_mean}')
        print(f'median value = {np.median(difference)*1000}')
    else:
        print(f'too much discrepency between fr first = {first_mean}, second = {second_mean}')
    
    framerate = 1000/first_mean
    print(f'first col framerate = {framerate}. second col framerate = {1000/second_mean}')
    print(framerate)
    return framerate


def calculate_light_peaks_from_roi (dataset_path, roi_path, framerate): #, data_reducer = 100):
    
    """input path to ROI h5 file generated from roi_results! and get out the light peaks in frames from ROI data.
    will save in h5 file in dataset_path"""

    
    with h5py.File(roi_path, 'r') as f:
        roi_data = f['roi data'][()]
        raw_light = f['raw light'][()]
    
    # find peaks
    light_median = np.median(raw_light)
    early_light_max = max(raw_light[0:2000])
    light_peaks, properties = scipy.signal.find_peaks(raw_light, height = early_light_max +.001, prominence = 20, distance = 10)
    #there is a condition that requires this, but I can't remember exactly what the data looked like
    if len(light_peaks) == 0:
        print("attempting new early_light_max, because no light peaks")
        early_light_max = max(light_data_column[0:100])
        #light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max +.001, prominence = .1, distance = 10)
        light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max*0.6, distance = 10)
        if len(light_peaks) == 0:
            print("There are still no light peaks, attempting with very low prominence")
            early_light_max = max(light_data_column[0:2000])
            light_peaks, properties = scipy.signal.find_peaks(light_data_column, height = early_light_max*0.6, prominence = .05, distance = 10)
            print(f'early light max 0:2000 {early_light_max}')
            if len(light_peaks) == 0:
                print("skipping this fly--no light peaks")
            
    
#     ## convert to seconds
#     voltage_framerate =  10000/data_reducer #frames/s # 1frame/.1ms * 1000ms/1s = 10000f/s
#     light_peaks_adjusted = light_peaks/voltage_framerate
    
    ##use time to give voltage in time
    ##light_peaks should be the indices of peaks => I can check the indices in time column
    light_peaks = np.array(light_peaks)
    

    #save light peaks
    light_peaks_path = os.path.join(dataset_path, 'light_peaks_roi.h5')
    #add_to_h5(light_peaks_path, 'light peaks ms', light_ms)
    
    
    add_to_h5(light_peaks_path, 'light peaks frames roi', light_peaks)
    add_to_h5(light_peaks_path, 'light peaks sec roi', light_peaks/framerate)
    add_to_h5(light_peaks_path, 'framerate used', framerate)
    return light_peaks


def get_roi_light_peaks (dataset_path, framerate = None):
    """get light peaks from roi_light_peaks.h5 file. Return light peaks in seconds. 
    Framerate will be used from roi peaks file unless otherwise specified. Should be video framerate"""
    
    roi_peaks_path = os.path.join(dataset_path, 'light_peaks_roi.h5')
    
    if framerate == None:
        with h5py.File(roi_peaks_path, 'r') as f:
            #print(f"framerate used {f['framerate used'][()]}")
            #roi_light_frames = f['light peaks frames roi'][()]
            roi_light_peaks_s = f['light peaks sec roi'][()]
    else:
        with h5py.File(roi_peaks_path, 'r') as f:
            print(f"used inputed framerate {framerate}")
            roi_light_frames = f['light peaks frames roi'][()]
            roi_light_peaks_s = roi_light_frames / framerate
        
    return roi_light_peaks_s