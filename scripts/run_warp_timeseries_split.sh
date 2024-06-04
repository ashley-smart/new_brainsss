#!/bin/bash
#SBATCH --job-name=warp_i
#SBATCH --time=7-00:00:00
#SBATCH --ntasks=2
#SBATCH --partition=trc
## comment out #SBATCH --mem 260G
#SBATCH --output=./logs/warp_mainlog.out
#SBATCH --open-mode=append
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date

python3 -u /home/users/asmart/projects/new_brainsss/scripts/run_warp_timeseries_split.py 
