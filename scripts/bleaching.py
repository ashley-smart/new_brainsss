import numpy as np
import sys
import os
import json
import matplotlib.pyplot as plt
from skimage.filters import threshold_triangle
import psutil
import brainsss
import nibabel as nib

def main(args):

    logfile = args['logfile']
    directory = args['directory']
    width = 120
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    files = args['files']

    #################
    ### Load Data ###
    #################

    
    data_mean = {}
    for file in files:
        full_file = os.path.join(directory, file)
        if os.path.exists(full_file):
            brain = np.asarray(nib.load(full_file).get_data(), dtype='uint16')
            data_mean[file] = np.mean(brain,axis=(0,1,2))
        else:
            printlog(F"Not found (skipping){file:.>{width-20}}")
            
        ## run bleaching correction and save bleach corrected brain -> consider using for rest of analysis, currently I'm not
        bleach_corr_brain = bleaching_correction(brain, sigma = 200)
        #save bleach corr brain
        if 'ch1' in file: color='red'
        elif 'ch2' in file: color='green'
        save_file = os.path.join(directory, 'bleach_corr_brain_{}.nii'.format(color))
        aff = np.eye(4)
        img = nib.Nifti1Image(bleach_corr_brain, aff)
        img.to_filename(save_file)
        bleach_corr_brain = None
        del bleach_corr_brain
        gc.collect()
       
       

    ##############################
    ### Output Bleaching Curve ###
    ##############################

    plt.rcParams.update({'font.size': 24})
    fig = plt.figure(figsize=(10,10))
    signal_loss = {}
    for file in data_mean:
        xs = np.arange(len(data_mean[file]))
        color='k'
#         if file[-1] == '1': color='red'
#         if file[-1] == '2': color='green'
        if 'ch1' in file: color='red'
        elif 'ch2' in file: color='green'
        plt.plot(data_mean[file],color=color,label=file)
        linear_fit = np.polyfit(xs, data_mean[file], 1)
        plt.plot(np.poly1d(linear_fit)(xs),color='k',linewidth=3,linestyle='--')
        signal_loss[file] = linear_fit[0]*len(data_mean[file])/linear_fit[1]*-100
    plt.xlabel('Frame Num')
    plt.ylabel('Avg signal')
    loss_string = ''
    for file in data_mean:
        if not np.isnan(signal_loss[file]):
            loss_string = loss_string + file + ' lost' + F'{int(signal_loss[file])}' +'%\n'
        else:
            printlog("Nan found")
            loss_string = file + 'nan'
    plt.title(loss_string, ha='center', va='bottom')
    # plt.text(0.5,0.9,
    #          loss_string,
    #          horizontalalignment='center',
    #          verticalalignment='center',
    #          transform=plt.gca().transAxes)

    save_file = os.path.join(directory, 'bleaching.png')
    plt.savefig(save_file,dpi=300,bbox_inches='tight')
    
    


##Luke's bleaching correction
def bleaching_correction(brain,sigma=200):
    """ Subtracts slow brain trends over time.
    Subtracts each voxel's slow-pass truncated gaussian filter from itself.
    The slow-pass filtering will be different for different speeds of aquisition since
    sigma is in units of indicies, not time. Not worrying about this for now since
    my imaging is all similar aquisition rates (2-3Hz).
    Parameters
    ----------
    brain: numpy array. Time must be axis=-1.
    sigma: sigma of gaussian filter. sigma=200 is default. At 2Hz aquisition, this is a
    200*(1/2Hz)*2 = 200sec or ~3min window of smoothing.
    Returns
    -------
    brain: original numpy array with slow trends subtracted."""

    print('brain_shape: {}'.format(np.shape(brain)))
    sys.stdout.flush()

    smoothed = scipy.ndimage.gaussian_filter1d(brain,sigma=sigma,axis=-1,truncate=1)
    brain = brain - smoothed
    return brain

if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
