#!/bin/bash
#SBATCH --job-name=full_vol
#SBATCH --time=4-00:00:00
#SBATCH --ntasks=1
#SBATCH --partition=trc
## comment out #SBATCH --mem 260G
#SBATCH --output=./logs/2023mainlog.out
#SBATCH --open-mode=append
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date

python3 -u /home/users/asmart/projects/new_brainsss/scripts/vol_main.py 
