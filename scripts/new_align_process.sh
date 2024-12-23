#!/bin/bash
#SBATCH --job-name=process
#SBATCH --partition=trc
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=./logs/processlog.out
#SBATCH --open-mode=append

ml python/3.6
date
python3 -u ./new_align_process.py