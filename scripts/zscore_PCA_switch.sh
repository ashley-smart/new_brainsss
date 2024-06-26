#!/bin/bash
#SBATCH --job-name=remlight_z_P
#SBATCH --time=7-00:00:00
#SBATCH --ntasks=1
#SBATCH --partition=trc
## comment out #SBATCH --mem 260G
#SBATCH --output=./logs/remlight_mainlog.out
#SBATCH --open-mode=append
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date

python3 -u /home/users/asmart/projects/new_brainsss/scripts/zscore_PCA_switch.py 
