#!/bin/bash
#SBATCH --job-name=stitch_nii_av
#SBATCH --partition=owners
#SBATCH --time=2-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=20
#SBATCH --mem-per-cpu=8G
#SBATCH --output=./logs/stitchlog.out
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL

ml python/3.6.1
# ml antspy/0.2.2
date
python3 -u /home/users/asmart/projects/brainsss_ash/scripts/stitch_nii_only.py
