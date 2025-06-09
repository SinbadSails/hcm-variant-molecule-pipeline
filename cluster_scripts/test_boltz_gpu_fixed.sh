#!/bin/bash
#SBATCH --job-name=test_boltz
#SBATCH --output=test_boltz_%j.out
#SBATCH --error=test_boltz_%j.err
#SBATCH --partition=amperenodes
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00

# Reset modules and load required modules
module reset
module load Python/3.11.5-GCCcore-13.2.0
module load CUDA/11.8.0
module load cuDNN/8.7.0.84-CUDA-11.8.0

# Activate virtual environment
source boltz-env/bin/activate

# Copy input files to local storage for better performance with A100s
echo "Copying files to local storage..."
mkdir -p /local/$USER/$SLURM_JOB_ID
cp domain_variant_gly584arg.yaml /local/$USER/$SLURM_JOB_ID/
cd /local/$USER/$SLURM_JOB_ID

# Check GPU availability
echo "Checking GPU availability:"
nvidia-smi

# Test boltz with a small prediction
echo "Testing boltz prediction:"
boltz predict domain_variant_gly584arg.yaml --use_msa_server --out_dir gpu_test_results --sampling_steps 10

# Copy results back to original directory
echo "Copying results back..."
cp -r gpu_test_results $SLURM_SUBMIT_DIR/

# Clean up local storage
echo "Cleaning up local storage..."
rm -rf /local/$USER/$SLURM_JOB_ID

echo "Job completed successfully at $(date)" 