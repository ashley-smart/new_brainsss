#!/bin/bash
#SBATCH --job-name=mean_brain
#SBATCH --partition=trc
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=./logs/mean_mainlog.out
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL

ml python/3.6
date
python3 -u /home/users/asmart/projects/new_brainsss/scripts/quick_ashley_mean.py