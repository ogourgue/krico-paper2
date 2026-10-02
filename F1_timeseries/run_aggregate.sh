#!/bin/bash
#SBATCH --job-name=p2_subarea
#SBATCH --qos=nf
#SBATCH --time=12:00:00
#SBATCH --mem=16G
#SBATCH --output=aggregate_subarea.%j.out
# Adjust --qos/--time to whatever F3's aggregate.py used on ECMWF HPC2020.
set -euo pipefail
export KRICO_POST=${KRICO_POST:-/scratch/cvan/KRICO/Post/Production}
cd "$(dirname "$0")"
python aggregate_subarea.py
