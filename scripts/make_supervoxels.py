import os
import sys
import json
import numpy as np
import h5py
import time

sys.path.append(os.path.split(os.path.dirname(__file__))[0])
sys.path.append("/home/users/asmart/projects/new_brainsss/")
os.listdir("/home/users/asmart/projects/new_brainsss/")
sys.path.append("/home/users/asmart/projects/new_brainsss/brainsss")
import brainsss
print(sys.path)

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.image import grid_to_graph

def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn
'''
Suppressing this warning from AgglomerativeClustering:
UserWarning: Persisting input arguments took 1.06s to run.
If this happens often in your code, it can cause performance problems
(results will be correct in all cases).
The reason for this is probably some large input arguments for a wrapped
 function (e.g. large strings).
THIS IS A JOBLIB ISSUE. If you can, kindly provide the joblib's team with an
 example so that they can fix the problem.
  **kwargs)
 '''

def main(args):  #added directory and file_names

	#func_path = args['func_path']
	logfile = args['logfile']
	directory = args['directory'] # full fly path Is the same as func_path
	file_names = args['file_names']  #should be highpass_zscore
	printlog = getattr(brainsss.Printlog(logfile=logfile), 'print_to_log')
	n_clusters = 2000 #prev 2000

	### LOAD BRAIN ###
	for brain_file in file_names:
		brain_path = os.path.join(directory, brain_file)	
		printlog(f'brain path = {brain_path}')	
		t0 = time.time()

		#brain_path = os.path.join(func_path, 'functional_channel_2_moco_zscore_highpass.h5')
		
		with h5py.File(brain_path, 'a') as h5_file:
			printlog(f'keys = {h5_file.keys()}')
			brain = np.nan_to_num(h5_file.get("zscore")[:].astype('float32'))
		printlog('brain shape: {}'.format(brain.shape))
		printlog('load duration: {} sec'.format(time.time()-t0))

		### MAKE CLUSTER DIRECTORY ###

		cluster_dir = os.path.join(directory, 'clustering')
		if not os.path.exists(cluster_dir):
			os.mkdir(cluster_dir)

		### FIT CLUSTERS ###

		printlog('fitting clusters')
		t0 = time.time()
		brain_dims = np.shape(brain)
		connectivity = grid_to_graph(brain_dims[0],brain_dims[1]) #previously grid_to_graph(256,128)
		cluster_labels = []
		for z in range(brain_dims[2]): #previously range(49):
			neural_activity = brain[:,:,z,:].reshape(-1, brain_dims[3]) #previously (-1, 3384)
			cluster_model = AgglomerativeClustering(n_clusters=n_clusters,
										memory=cluster_dir,
										linkage='ward',
										connectivity=connectivity)
			cluster_model.fit(neural_activity)
			cluster_labels.append(cluster_model.labels_)
		cluster_labels = np.asarray(cluster_labels)
		save_file = os.path.join(cluster_dir, f'cluster_labels_{n_clusters}.npy')
		np.save(save_file,cluster_labels)
		printlog('cluster fit duration: {} sec'.format(time.time()-t0))

		### GET CLUSTER AVERAGE SIGNAL ###

		printlog('getting cluster averages')
		t0 = time.time()
		all_signals = []
		for z in range(brain_dims[2]): #previously range(49):
			neural_activity = brain[:,:,z,:].reshape(-1, brain_dims[3]) #previously (-1, 3384)
			signals = []
			for cluster_num in range(n_clusters):
				cluster_indicies = np.where(cluster_labels[z,:]==cluster_num)[0]
				mean_signal = np.mean(neural_activity[cluster_indicies,:], axis=0)
				signals.append(mean_signal)
			signals = np.asarray(signals)
			all_signals.append(signals)
		all_signals = np.asarray(all_signals)
		save_file = os.path.join(cluster_dir, f'cluster_signals_{n_clusters}.npy')
		np.save(save_file, all_signals)
		printlog('cluster average duration: {} sec'.format(time.time()-t0))

if __name__ == '__main__':
	print(f' arg {sys.argv}')
	main(json.loads(sys.argv[1]))