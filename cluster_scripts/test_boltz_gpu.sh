#!/bin/bash
#SBATCH --job-name=test_boltz
#SBATCH --output=test_boltz_%j.out
#SBATCH --error=test_boltz_%j.err
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:a100:1
#SBATCH --time=02:00:00

# Load required modules
module load Python/3.11.5-GCCcore-13.2.0

# Activate virtual environment
source boltz-env/bin/activate

# Check GPU availability
echo "Checking GPU availability:"
nvidia-smi

# Test boltz with a small prediction
echo "Testing boltz prediction:"
boltz predict domain_variant_gly584arg.yaml --use_msa_server --out_dir gpu_test_results --sampling_steps 10

echo "Job completed at $(date)" 