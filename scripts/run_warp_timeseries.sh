#!/bin/bash
#SBATCH --job-name=warp
#SBATCH --partition=trc
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=./logs/warplog.out
#SBATCH --open-mode=append

ml python/3.6
date
python3 -u /home/users/asmart/projects/new_brainsss/scripts/warp_timeseries.py