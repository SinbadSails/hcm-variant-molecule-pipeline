# 🧬 HCM Variant Analysis - Slurm A100 GPU Guide

## Overview

This guide helps you run Boltz-2 protein structure predictions for HCM variants on UAB's Cheaha cluster using A100 GPUs with 80GB memory. This will solve your memory issues and dramatically speed up predictions.

## 🚀 Quick Start

### 1. Initial Setup (One-time)

```bash
# Make setup script executable
chmod +x setup_slurm_environment.sh

# Run the setup (this will take 10-15 minutes)
./setup_slurm_environment.sh
```

### 2. Submit Your First Job

```bash
# Submit a single variant
./submit_boltz_jobs.sh --single variant_gly584arg.yaml

# OR submit all variants as an array job
./submit_boltz_jobs.sh --array
```

### 3. Monitor Your Jobs

```bash
# Check job status
./submit_boltz_jobs.sh --queue

# Check results
./submit_boltz_jobs.sh --results
```

## 📁 Files Created

| File | Purpose |
|------|---------|
| `slurm_boltz_single.job` | Submit single variant prediction |
| `slurm_boltz_array.job` | Submit multiple variants (array job) |
| `submit_boltz_jobs.sh` | Easy job submission script |
| `setup_slurm_environment.sh` | One-time environment setup |
| `environment_slurm.yml` | Updated conda environment with GPU support |
| `SLURM_GUIDE.md` | This guide |

## 🔧 Detailed Usage

### Single Job Submission

```bash
# Submit specific variant
./submit_boltz_jobs.sh -s variant_gly584arg.yaml

# Monitor specific job
squeue -j JOB_ID

# View results
ls results_variant_gly584arg/
```

### Array Job Submission

```bash
# Submit all variants (max 2 concurrent)
./submit_boltz_jobs.sh -a

# Monitor array job
squeue -u $USER

# Results will be in separate directories:
# - results_variant_gly584arg/
# - results_variant_arg249gln/
# - results_domain_variant_gly584arg/
# - results_myh7_gly584arg/
```

### Monitoring and Management

```bash
# Check all your jobs
squeue -u $USER

# Check GPU partition status
sinfo -p amperenodes

# Cancel a job
scancel JOB_ID

# View job details
sacct -j JOB_ID --format=JobID,JobName,State,ExitCode,MaxRSS,AllocGRES
```

## 🎯 Optimizations for A100 GPUs

### Memory and Performance
- **80GB GPU memory**: No more "out of memory" errors
- **Local scratch**: Input files copied to fast NVMe storage
- **16 CPU cores**: Optimal for A100 GPU feeding
- **64GB RAM**: Plenty for preprocessing

### Job Configuration
- **2 hours**: Default time limit (adjust if needed)
- **200 sampling steps**: High quality predictions
- **Automatic cleanup**: Local scratch cleaned after job

## 📊 Your HCM Variants

Based on your `boltz2_status.txt`, you're working with:

1. **Gly584Arg** (AlphaMissense: 0.9951) - Very high pathogenicity
2. **Arg249Gln** (AlphaMissense: 0.9779) - Very high pathogenicity  
3. **Domain variants** - Structural analysis variants

## 🔬 Expected Performance

### Time Estimates (A100 vs Local)
- **Local machine**: 30-60 minutes + memory issues
- **A100 GPU**: 15-25 minutes with 200 sampling steps
- **No memory issues**: 80GB vs your local RAM limitations

### Quality Improvements
- **Higher sampling steps**: 200 vs 50-100 locally
- **Better convergence**: No memory pressure
- **Reproducible results**: Consistent cluster environment

## 🛠 Troubleshooting

### Common Issues

#### Job Fails to Start
```bash
# Check partition availability
sinfo -p amperenodes

# Check your job queue
squeue -u $USER
```

#### Environment Issues
```bash
# Reload environment
module reset
module load CUDA/12.2.0 cuDNN/8.9.2.26-CUDA-12.2.0 Anaconda3
conda activate hcm-pipeline
```

#### Results Not Found
```bash
# Check job output
cat boltz_variants_JOBID_ARRAYID.out
cat boltz_variants_JOBID_ARRAYID.err

# Check if job completed
sacct -j JOBID
```

### Job Status Meanings
- **PD**: Pending (waiting for resources)
- **R**: Running
- **CG**: Completing 
- **CD**: Completed
- **F**: Failed
- **CA**: Cancelled

## 📈 Monitoring Your Research Progress

### Track Prediction Success
```bash
# Count completed predictions
ls results_*/prediction_summary_*.txt | wc -l

# Check prediction quality
grep -r "confidence" results_*/

# View structure files
ls results_*/*.pdb
```

### Publication-Ready Analysis
Your results will include:
- High-confidence protein structures
- Confidence scores for each residue
- MSA alignment data
- Detailed prediction logs

## 🎯 Next Steps for Your Research

### Immediate Actions
1. **Run all high-priority variants** with array job
2. **Analyze structural differences** between variants
3. **Identify drug binding sites** in predicted structures

### Future Experiments
1. **Protein-drug docking** using predicted structures
2. **Molecular dynamics simulations** on Cheaha
3. **Comparative analysis** with AlphaFold structures

## 💡 Pro Tips

### Efficient Workflow
```bash
# Create aliases for common commands
source ~/.bashrc  # Loads the aliases created by setup

# Use short commands
boltz-submit -a          # Submit array job
boltz-queue             # Check queue
boltz-results           # List results
```

### Resource Optimization
- **Use array jobs** for multiple variants
- **Monitor job efficiency** with `sacct`
- **Request appropriate time** (don't over-request)

### Data Management
- **Archive completed results** to prevent loss
- **Clean up old Slurm logs** periodically
- **Backup important configurations**

## 🔬 Research Impact

This setup positions you to:
- **Be among the first** to use Boltz-2 for HCM research
- **Generate high-quality structures** for drug discovery
- **Accelerate therapeutic development** with AI-predicted structures
- **Publish breakthrough results** combining HCM genetics with state-of-the-art AI

## 📞 Support

### Cheaha Support
- Email: `support@listserv.uab.edu`
- Documentation: [Cheaha User Guide](https://docs.rc.uab.edu/)

### Script Issues
Check error logs and job outputs first:
```bash
./submit_boltz_jobs.sh -r  # Review results and logs
```

## 🎉 Success Indicators

You'll know everything is working when:
- ✅ Jobs submit without errors
- ✅ GPU memory utilization ~80GB
- ✅ PDB files generated in results directories
- ✅ Prediction confidence scores > 70%

**Your HCM variant research is now supercharged with A100 GPUs!** 🚀 

cat > submit_publication_jobs.sh << 'EOF'
#!/bin/bash

echo "🚀 SUBMITTING PUBLICATION JOBS FOR HCM VARIANTS"

mkdir -p publication_results

VARIANTS=(
    "variant_gly584arg.yaml"
    "variant_arg249gln.yaml"
    "domain_variant_gly584arg.yaml"
    "myh7_gly584arg.yaml"
)

echo "📋 Submitting ${#VARIANTS[@]} high-priority variants:"

for variant in "${VARIANTS[@]}"; do
    if [ -f "$variant" ]; then
        echo "  ✅ Submitting: $variant"
        sbatch slurm_boltz_publication.job "$variant"
    else
        echo "  ❌ File not found: $variant"
    fi
done

echo ""
echo "📊 Check job status with: squeue -u $USER"
echo "📁 Results will be saved to: publication_results/"
EOF

chmod +x submit_publication_jobs.sh 