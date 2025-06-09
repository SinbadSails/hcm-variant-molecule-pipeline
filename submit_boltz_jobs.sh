#!/bin/bash

# 🚀 HCM Variant Boltz Prediction Submission Script
# UAB Cheaha Cluster - A100 GPU Jobs

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}=========================================="
echo "🧬 HCM Variant Boltz Prediction Submitter"
echo "=========================================="
echo -e "${NC}"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --single FILE     Submit single variant prediction"
    echo "  -a, --array          Submit array job for all variants"
    echo "  -l, --list           List available YAML files"
    echo "  -q, --queue          Check job queue status"
    echo "  -r, --results        Check results directories"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --single variant_gly584arg.yaml"
    echo "  $0 --array"
    echo "  $0 --queue"
    exit 1
}

# Function to check if on Cheaha
check_cluster() {
    if [[ ! -f "/etc/os-release" ]] || ! grep -q "cheaha" /etc/os-release 2>/dev/null; then
        if [[ ! "$HOSTNAME" =~ cheaha ]] && [[ ! "$HOSTNAME" =~ login ]]; then
            echo -e "${YELLOW}⚠️  Warning: You may not be on the Cheaha cluster${NC}"
            echo "Make sure you're logged into Cheaha before submitting jobs"
        fi
    fi
}

# Function to list YAML files
list_yaml_files() {
    echo -e "${GREEN}📋 Available YAML files:${NC}"
    ls -la *.yaml 2>/dev/null || echo "No YAML files found in current directory"
    echo ""
}

# Function to check job queue
check_queue() {
    echo -e "${GREEN}📊 Current job queue status:${NC}"
    echo "Your jobs:"
    squeue -u $USER --format="%.10i %.20j %.8T %.10M %.6D %.20S" || echo "No jobs in queue"
    echo ""
    echo "GPU partition status:"
    sinfo -p amperenodes --format="%.15P %.5a %.10l %.6D %.6t %.15C %.8z %.8m %.8G %.15f" || echo "Cannot check partition status"
    echo ""
}

# Function to check results
check_results() {
    echo -e "${GREEN}📁 Results directories:${NC}"
    ls -la results_* 2>/dev/null || echo "No results directories found"
    echo ""
    echo -e "${GREEN}📊 Slurm output files:${NC}"
    ls -la boltz_*.out boltz_*.err 2>/dev/null || echo "No slurm output files found"
    echo ""
}

# Function to submit single job
submit_single() {
    local yaml_file="$1"
    
    if [[ ! -f "$yaml_file" ]]; then
        echo -e "${RED}❌ Error: YAML file '$yaml_file' not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}🚀 Submitting single Boltz prediction job...${NC}"
    echo "YAML file: $yaml_file"
    
    job_id=$(sbatch --export=YAML_FILE="$yaml_file" slurm_boltz_single.job | awk '{print $4}')
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Job submitted successfully!${NC}"
        echo "Job ID: $job_id"
        echo "Monitor with: squeue -j $job_id"
        echo "Cancel with: scancel $job_id"
    else
        echo -e "${RED}❌ Job submission failed${NC}"
        exit 1
    fi
}

# Function to submit array job
submit_array() {
    echo -e "${GREEN}🚀 Submitting Boltz array job for multiple variants...${NC}"
    
    # Check if required files exist
    yaml_files=("variant_gly584arg.yaml" "variant_arg249gln.yaml" "domain_variant_gly584arg.yaml" "myh7_gly584arg.yaml")
    missing_files=()
    
    for file in "${yaml_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Warning: Some YAML files are missing:${NC}"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Submission cancelled"
            exit 1
        fi
    fi
    
    job_id=$(sbatch slurm_boltz_array.job | awk '{print $4}')
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Array job submitted successfully!${NC}"
        echo "Job ID: $job_id"
        echo "This will run up to 5 variants with maximum 2 concurrent jobs"
        echo "Monitor with: squeue -j $job_id"
        echo "Cancel with: scancel $job_id"
        echo ""
        echo -e "${BLUE}💡 Tips:${NC}"
        echo "- Results will be saved in results_<variant_name>/ directories"
        echo "- Each job uses 1 A100 GPU with 80GB memory"
        echo "- Jobs will automatically clean up local scratch space"
        echo "- Check progress with: squeue -u $USER"
    else
        echo -e "${RED}❌ Array job submission failed${NC}"
        exit 1
    fi
}

# Main script logic
check_cluster

case "$1" in
    -s|--single)
        if [[ -z "$2" ]]; then
            echo -e "${RED}❌ Error: YAML file not specified${NC}"
            usage
        fi
        submit_single "$2"
        ;;
    -a|--array)
        submit_array
        ;;
    -l|--list)
        list_yaml_files
        ;;
    -q|--queue)
        check_queue
        ;;
    -r|--results)
        check_results
        ;;
    -h|--help|"")
        usage
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        usage
        ;;
esac

echo -e "${BLUE}=========================================="
echo "🧬 HCM Boltz Prediction Submitter Complete"
echo -e "===========================================${NC}" 