#!/bin/bash
#SBATCH --job-name=testzscore
#SBATCH --partition=trc
#SBATCH --time=6-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8

#SBATCH --output=./logs/zscoretest.out
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date
python3 -u /home/users/asmart/projects/new_brainsss/scripts/vol_zscore_test.py
