#!/bin/bash
#SBATCH --job-name=mean_brain
#SBATCH --partition=trc
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=./logs/mean_mainlog.out
#SBATCH --open-mode=append

ml python/3.6
date
python3 -u ./make_mean_brain.py