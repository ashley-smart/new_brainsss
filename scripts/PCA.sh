#!/bin/bash
#SBATCH --job-name=PCA
#SBATCH --partition=trc
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24

#SBATCH --output=./logs/PCAlog.out
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL
# Params: (1) experiment_date

ml python/3.6.1
# ml antspy/0.2.2
date

experiment_date=$1
python3 -u /home/users/asmart/projects/new_brainsss/scripts/PCA.py $experiment_date