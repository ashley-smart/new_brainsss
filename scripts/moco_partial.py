import sys
import os
import json
import nibabel as nib
import numpy as np
import brainsss
import warnings
import ants
warnings.filterwarnings("ignore")

#sys.path.insert(0, '/home/users/brezovec/.local/lib/python3.6/site-packages/lib/python/')
import ants

def main(args):
    files = args['files'] # need all stitched files
    
    logfile = args['logfile']
    directory = args['directory'] # directory will be a full path to either an anat folder or a func folder
    start = int(args['start'])
    stop = int(args['stop'])
    printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
    #printlog("MOCO FILES", files)

    moco_dir = os.path.join(directory, 'moco')

    try:
      for file in files:
          if 'ch1_stitched.nii' in file:
              master_path = os.path.join(directory, file)
              printlog("ch1 stitched found and master path created")
          elif 'ch2_stitched.nii' in file:
              moving_path = os.path.join(directory, file)  #in moco.py moving brain will be saved as green
          elif 'ch1_stitched_mean' in file: 
              master_path_mean = os.path.join(directory, file)

      # For the sake of memory, load only the part of the brain we will need.
      master_brain = load_partial_brain(master_path,start,stop)
      moving_brain = load_partial_brain(moving_path,start,stop)
      mean_brain = ants.from_numpy(np.asarray(nib.load(master_path_mean).get_data(), dtype='float32'))
    except:
      printlog('fuctional data not found')
      printlog(os.path.join(directory, file))
#       master_path = os.path.join(directory, 'anatomy_channel_1.nii')
#       moving_path = os.path.join(directory, 'anatomy_channel_2.nii')
#       master_path_mean = os.path.join(directory, 'anatomy_channel_1_mean.nii')

#       # For the sake of memory, load only the part of the brain we will need.
#       master_brain = load_partial_brain(master_path,start,stop)
#       moving_brain = load_partial_brain(moving_path,start,stop)
#       mean_brain = ants.from_numpy(np.asarray(nib.load(master_path_mean).get_data(), dtype='float32'))

    brainsss.motion_correction(master_brain,
                           moving_brain,
                           moco_dir,
                           printlog,
                           mean_brain,
                           suffix='_'+str(start))
    
def load_partial_brain(file, start, stop):
    brain = nib.load(file).dataobj[:,:,:,start:stop]
    # for ants, supported_ntypes = {'uint8', 'uint32', 'float32', 'float64'}
    brain = ants.from_numpy(np.asarray(np.squeeze(brain), dtype='float32')) #updated dtype 20200626 from float64 to float32
    # always keep 4 axes:
    if len(np.shape(brain)) == 3:
      brain = brain[:,:,:,np.newaxis]
    return brain
    
    
    
##### NEW STRATEGY ####    
    
def load_brain_by_volume(ch1_file, ch2_file, save_directory):
    ch1_proxy = nib.load(ch1_file) #low memory loading, doesn't actually load brain
    ch2_proxy = nib.load(ch2_file)
    dims = ch1_proxy.header.get_data_shape()
    number_volumes = dims[-1] 
    #motion correct each volume and save
    for i in range(number_volumes):
        ##in progress -- need to sort out if fixed brain should be mean or ch1? I think ch1 since master is ch1
        ch1_brain = ch1_proxy.dataobj[...,i] #one volume
        ch2_brain = ch2_proxy.dataobj[...,i]
       #make this meanch1 master_brain = ants.from_numpy(np.asarray(ch1_brain, dtype = 'float32'))
        moving_brain = ants.from_numpy(np.asarray(ch2_brain, dtype = 'float32'))
        moco_by_vol = ants.registration(mean-tdtom, moving_brain, type_of_transfor, = 'SyN')
        #save each moco volume
        # ? how? I think it is a dictionary. Should I save the whole thing?
        #luke saves parts of the dictionary (warpedbrain (warpmoveout), warpedfixedout (what already put intothe ants--don't need to save this),parameters that it used to warp (warpparameters--need to apply these to channel 2)
        
#         def save_motCorr_brain(brain, directory, suffix):
#     brain = np.moveaxis(np.asarray(brain),0,3)
#     save_file = os.path.join(directory, 'motcorr_' + suffix + '.nii')
#     aff = np.eye(4)
#     img = nib.Nifti1Image(brain, aff)
#     img.to_filename(save_file)

        
        
        
        
        


if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
