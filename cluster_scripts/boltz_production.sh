#!/bin/bash
#SBATCH --job-name=boltz_prod
#SBATCH --output=boltz_prod_%j.out
#SBATCH --error=boltz_prod_%j.err
#SBATCH --partition=amperenodes
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00

# Reset modules and load required modules
module reset
module load Python/3.11.5-GCCcore-13.2.0
module load CUDA/11.8.0

# Set SSL certificate variables
export SSL_CERT_DIR=/etc/ssl/certs
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Activate virtual environment
source boltz-env/bin/activate

# Copy input files to local storage
echo "Copying files to local storage..."
mkdir -p /local/$USER/$SLURM_JOB_ID
cp $INPUT_FILE /local/$USER/$SLURM_JOB_ID/
cd /local/$USER/$SLURM_JOB_ID

# Check GPU availability
echo "Checking GPU availability:"
nvidia-smi

# Run boltz prediction
echo "Running boltz prediction on: $INPUT_FILE"
boltz predict $(basename $INPUT_FILE) --out_dir results --sampling_steps 50

# Copy results back
echo "Copying results back..."
cp -r results $SLURM_SUBMIT_DIR/results_$(basename $INPUT_FILE .yaml)

# Clean up
rm -rf /local/$USER/$SLURM_JOB_ID

echo "Job completed successfully at $(date)"
