"""align anatomical brain to functional brain and warp to brain template---based off of Luke's preprocess code. 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py

His instructions:
1) align func to anat (for an individual fly)
(brainsss function func2anat), see 
https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 507
can run using preprocess and the --f2a flag
2) align anat to whatever template you are using (the final space for your data). I use "/oak/stanford/groups/trc/data/Brezovec/2P_Imaging/anat_templates/20220301_luke_2_jfrc_affine_zflip_2umiso.nii"
(brainsss function anat2anat), see 

https://github.com/ClandininLab/brainsss/blob/main/scripts/preprocess.py
starting at line 582
can run using preprocess and the --a2a flag

3) use these two transforms to apply to whatever neural data you want to warp. You can either warp in single maps you calculated in the original space (like a correlation map), or the entirety of your functional recording. For the former, the code will look something like
https://github.com/ClandininLab/brainsss/blob/main/brainsss/brain_utils.py
check out warp_STA_brain function.

If you want to warp the full recording, check out
https://github.com/lukebrez/dataflow/blob/master/sherlock_scripts/apply_transforms_to_raw_data.py
Make sure the voxel sizes are always set correctly, using
fixed.set_spacing(fixed_resolution)
and make sure the z-direction matches (ie either anterior to posterior or vica versa for the func,anat,and template.)

"""

