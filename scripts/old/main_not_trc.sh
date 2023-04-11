#!/bin/bash
#SBATCH --job-name=bm_brainsss_ash
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --partition=bigmem
#SBATCH --mem 260G
#SBATCH --output=./logs/mainlog.out
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date
python3 -u /home/users/asmart/projects/brainsss_ash/scripts/main.py
