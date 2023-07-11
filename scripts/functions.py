## final function to get switch times!
def get_brain_t_switch_set(dataset_path, exp_length1 = 20, exp_length2 = 40):
    """returns array of arrays of switch times that correspond to index in t of brains.
    returns seperately 20 and 40s experiemnts
    20s_t_points = [[start1 stop1] [start 2 stop2]]
    *takes time from average time across all z for one brain slice to get t brain slice"""
    
    light_peaks_twenty_times, light_peaks_forty_times = get_times_switch_blocks (dataset_path, exp_length1, exp_length2)
    timestamps = load_timestamps(dataset_path)
    average_timestamps = np.mean(timestamps, axis = 1)/1000  ##to convert ms to s to match light_peaks
    
    twenty_switch_set_t = []
    forty_switch_set_t = []
    for switch_set in light_peaks_twenty_times:
        start_time = switch_set[0]
        end_time = switch_set[1]
        start_time_index = np.where(average_timestamps < start_time)[0][-1]
        end_time_index = np.where(average_timestamps < end_time)[0][-1]
        both = both = (start_time_index, end_time_index)
        twenty_switch_set_t.append(both)

    for switch_set in light_peaks_forty_times:
        start_time = switch_set[0]
        end_time = switch_set[1]
        start_time_index = np.where(average_timestamps < start_time)[0][-1]  #np.where needs 0 index and then want the last element
        end_time_index = np.where(average_timestamps < end_time)[0][-1]
        both = both = (start_time_index, end_time_index)
        forty_switch_set_t.append(both)
    twenty_switch_set_t = np.array(twenty_switch_set_t)
    forty_switch_set_t = np.array(forty_switch_set_t)
    return twenty_switch_set_t, forty_switch_set_t

def get_times_switch_blocks (dataset_path, exp_length1 = 20, exp_length2 = 40):
    """returns array of arrays of times in s that each block 
    starts and ends seperate arrays returned for 20 and 40 (or specified expt times)
    i.e. 20s_times = [[30.9 400.2][600.7  987.6]]  [[start1 stop 1] [start 2 stop 2]] """
    
    light_peaks = get_light_peaks(dataset_path)
    twenty, forty = get_switch_start_stop_indices(dataset_path, exp_length1, exp_length2)
    
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
def get_switch_start_stop_indices(dataset_path, exp_length1 = 20, exp_length2 = 40):
    """returns an array of tuples of start and stop indices for starts and stops of 20s or 40s. 
    20 and 40 are returned in seperate arrays.
    inclusive (start = first index and stop = last index)"""
    switch_points = find_switch_points(dataset_path)
    light_peaks = get_light_peaks (dataset_path)
    light_times = light_peaks[1:]- light_peaks[0:-1]
    twenty = []
    forty = []
    for i in range(len(switch_points)):
        switch_index = switch_points[i] #plus 1 to account for 
        print(switch_index)
        print(light_times[switch_index])
        if i == 0:
            if exp_length1 - 5 < light_times[switch_index] < exp_length1 + 5:
                t = (0, switch_index)
                twenty.append(t)
            elif exp_length2 - 5 < light_times[switch_index] < exp_length2 + 5:
                t = (0, switch_index)
                forty.append(t)
        else:
            previous_index = switch_points[i - 1] + 1
            if exp_length1 - 5 < light_times[switch_index] < exp_length1 + 5:
                t = (previous_index, switch_index)
                twenty.append(t)
            elif exp_length2 - 5 < light_times[switch_index] < exp_length2 + 5:
                t = (previous_index, switch_index)
                forty.append(t)
    twenty = np.array(twenty)
    forty = np.array(forty)
    return twenty, forty


def find_switch_points(dataset_path):
    """input fly folder containing voltage file, returns indices of the last trial before switch"""
    light_peaks = get_light_peaks (dataset_path)
    light_times = light_peaks[1:]- light_peaks[0:-1]
    light_times_diff = np.rint(abs(light_times[1:] - light_times[0:-1]))
    switch = np.where(light_times_diff > 15)[0]  #switch is the index of the last trial of the current time
    switch = np.array(switch)
    return switch

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
        print('Trying to load timestamp data from hdf5 file.')
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
    
    print('Success.')
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
        print("attempting new early_light_max, because no light peaks")
        early_light_max = max(light_column[0:100])
        light_peaks, properties = scipy.signal.find_peaks(light_column, height = early_light_max +.001, prominence = .1, distance = 10)
        
        if len(light_peaks) == 0:
            print("There are still no light peaks for " + str(date) + " " + str(fly))
            print("skipping this fly--no light peaks")
            
    
    ## convert to seconds
    voltage_framerate =  10000/data_reducer #frames/s # 1frame/.1ms * 1000ms/1s = 10000f/s
    light_peaks_adjusted = light_peaks/voltage_framerate
    
    return light_peaks_adjusted


def find_moco_file(Path):
    """path should be fly folder. This returns the path to the moco ch2 h5 file"""
    for name in os.listdir(fly_path):
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
    """adds new key value to h5 file and checks if it already exists
    does overwrite"""
    with h5py.File(Path, 'a') as f:
        if key not in f.keys(): #check if key already in file
            f[key] = value
        else:
            del f[key]
            #print('deleting old key and OVERWRITING')
            f[key] = value
            
            
            
def run_PCA (Path, n_components, key = 'data'):
    """input path to moco file. will default to do non-zscore data, but can specify another key (i.e. 'zscore'). 
    Returns loadings and components reshaped back to n_components, x, y, z"""
    
    t_batch = 200 #number of timepoints to run

    with h5py.File(Path, 'r') as hf:  
        moco_data = hf[key]  
        dims = np.shape(moco_data) #x,y,z,t
    #     ##remove first 3 z slices
    #     moco_data = moco_data[:,:,3:,:] #to get rid of first 3 z slices
    #     dims = np.shape(moco_data)

        #run through batches of t so it can load in memory
        windows = np.arange(0,dims[-1], t_batch)
        transformer = IncrementalPCA(n_components = n_components)

        for window_index in range(len(windows)):
            if windows[window_index] == windows[-1]: #last case go to end of dims (dims[-1])
                moco_data_subset = np.array(moco_data[:,:,:, windows[window_index]:dims[-1]])
                moco_data_reshaped = np.reshape(moco_data_subset, (np.prod(dims[0:3]), -1)).T  #so xyz is column and t is row
                transformer.partial_fit(moco_data_reshaped)
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
    total_timepoints = steps[1] - steps[0]
    for chunk_num in range(len(steps) - 1):  
        chunk_start = steps[chunk_num]
        chunk_end = steps[chunk_num + 1]
        chunk = data[:,:,:,chunk_start:chunk_end] #I'm doing chunks on t
        s = np.sum((chunk - meanbrain)**2, axis = 3, keepdims = True) #changed to sum of chunk
        total = s + total
    final_std = np.sqrt(total/total_timepoints) #fix this from len
    return final_std
    

