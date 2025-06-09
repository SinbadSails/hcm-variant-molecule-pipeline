#!/bin/bash

# 🚀 HCM Variant Analysis - Slurm Environment Setup
# UAB Cheaha Cluster Setup Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "🧬 HCM Variant Analysis - Slurm Setup"
echo "=========================================="
echo -e "${NC}"

# Function to check if we're on Cheaha
check_cluster() {
    echo -e "${BLUE}🔍 Checking cluster environment...${NC}"
    
    if command -v squeue &> /dev/null; then
        echo -e "${GREEN}✅ Slurm commands available${NC}"
    else
        echo -e "${RED}❌ Slurm not available - make sure you're on Cheaha${NC}"
        exit 1
    fi
    
    if command -v module &> /dev/null; then
        echo -e "${GREEN}✅ Module system available${NC}"
    else
        echo -e "${RED}❌ Module system not available${NC}"
        exit 1
    fi
    
    # Check partition availability
    if sinfo -p amperenodes &> /dev/null; then
        echo -e "${GREEN}✅ A100 GPU partition (amperenodes) available${NC}"
    else
        echo -e "${YELLOW}⚠️  A100 GPU partition may not be available${NC}"
    fi
}

# Function to setup conda environment
setup_conda() {
    echo -e "${BLUE}🐍 Setting up conda environment...${NC}"
    
    # Load Anaconda module
    module reset
    module load Anaconda3
    
    # Check if environment already exists
    if conda env list | grep -q "hcm-pipeline"; then
        echo -e "${YELLOW}⚠️  Environment 'hcm-pipeline' already exists${NC}"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Removing existing environment..."
            conda env remove -n hcm-pipeline -y
        else
            echo "Using existing environment"
            return
        fi
    fi
    
    echo "Creating conda environment from environment_slurm.yml..."
    if [[ -f "environment_slurm.yml" ]]; then
        conda env create -f environment_slurm.yml
    else
        echo -e "${RED}❌ environment_slurm.yml not found${NC}"
        echo "Creating basic environment..."
        conda create -n hcm-pipeline python=3.10 -y
    fi
    
    echo -e "${GREEN}✅ Conda environment setup complete${NC}"
}

# Function to install Boltz
install_boltz() {
    echo -e "${BLUE}🧬 Installing Boltz-2...${NC}"
    
    module reset
    module load Anaconda3
    conda activate hcm-pipeline
    
    echo "Installing Boltz dependencies..."
    # Install PyTorch with CUDA support first
    conda install pytorch pytorch-cuda=12.1 -c pytorch -c nvidia -y
    
    # Install transformers and other ML libraries
    pip install transformers accelerate datasets tokenizers huggingface_hub safetensors einops lightning
    
    # Try to install Boltz
    echo "Installing Boltz..."
    if pip install boltz; then
        echo -e "${GREEN}✅ Boltz installed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Boltz pip install failed, trying GitHub installation...${NC}"
        if pip install git+https://github.com/deepmind/boltz.git; then
            echo -e "${GREEN}✅ Boltz installed from GitHub${NC}"
        else
            echo -e "${RED}❌ Boltz installation failed${NC}"
            echo "You may need to install Boltz manually"
        fi
    fi
    
    # Test Boltz installation
    echo "Testing Boltz installation..."
    if python -c "import boltz; print('Boltz version:', boltz.__version__)" 2>/dev/null; then
        echo -e "${GREEN}✅ Boltz import successful${NC}"
    else
        echo -e "${YELLOW}⚠️  Boltz import test failed - you may need to install manually${NC}"
    fi
}

# Function to setup directory structure
setup_directories() {
    echo -e "${BLUE}📁 Setting up directory structure...${NC}"
    
    # Create necessary directories
    mkdir -p slurm_logs
    mkdir -p results_archive
    mkdir -p backup_configs
    
    echo -e "${GREEN}✅ Directory structure created${NC}"
}

# Function to make scripts executable
make_executable() {
    echo -e "${BLUE}🔧 Making scripts executable...${NC}"
    
    chmod +x submit_boltz_jobs.sh
    chmod +x slurm_boltz_single.job
    chmod +x slurm_boltz_array.job
    chmod +x setup_slurm_environment.sh
    
    echo -e "${GREEN}✅ Scripts are now executable${NC}"
}

# Function to test GPU access
test_gpu_access() {
    echo -e "${BLUE}🧪 Testing GPU access...${NC}"
    
    # Submit a quick test job
    cat > gpu_test.job << 'EOF'
#!/bin/bash
#SBATCH --job-name=gpu_test
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --gres=gpu:1
#SBATCH --partition=amperenodes
#SBATCH --time=00:05:00
#SBATCH --output=gpu_test_%j.out
#SBATCH --error=gpu_test_%j.err

module reset
module load CUDA/12.2.0
module load Anaconda3

echo "GPU Test Results:"
echo "Node: $SLURMD_NODENAME"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
nvidia-smi
echo "Test completed successfully"
EOF

    echo "Submitting GPU test job..."
    job_id=$(sbatch gpu_test.job | awk '{print $4}')
    echo "Test job submitted with ID: $job_id"
    echo "Check results with: cat gpu_test_${job_id}.out"
    echo "Monitor with: squeue -j $job_id"
}

# Function to create helpful aliases
create_aliases() {
    echo -e "${BLUE}🔗 Creating helpful aliases...${NC}"
    
    cat >> ~/.bashrc << 'EOF'

# HCM Variant Analysis Aliases
alias boltz-submit='./submit_boltz_jobs.sh'
alias boltz-queue='squeue -u $USER'
alias boltz-results='ls -la results_*'
alias gpu-nodes='sinfo -p amperenodes'
alias load-hcm='module reset && module load CUDA/12.2.0 cuDNN/8.9.2.26-CUDA-12.2.0 Anaconda3 && conda activate hcm-pipeline'
EOF

    echo -e "${GREEN}✅ Aliases added to ~/.bashrc${NC}"
    echo "Run 'source ~/.bashrc' or start a new session to use them"
}

# Function to display final instructions
final_instructions() {
    echo -e "${BLUE}=========================================="
    echo "🎉 Setup Complete!"
    echo "=========================================="
    echo -e "${NC}"
    
    echo -e "${GREEN}📋 Next Steps:${NC}"
    echo "1. Source your bashrc: source ~/.bashrc"
    echo "2. Test the environment: conda activate hcm-pipeline"
    echo "3. Submit a test job: ./submit_boltz_jobs.sh --single variant_gly584arg.yaml"
    echo "4. Monitor jobs: ./submit_boltz_jobs.sh --queue"
    echo ""
    
    echo -e "${BLUE}💡 Useful Commands:${NC}"
    echo "• Submit single job: ./submit_boltz_jobs.sh -s variant_file.yaml"
    echo "• Submit all variants: ./submit_boltz_jobs.sh -a"
    echo "• Check queue: ./submit_boltz_jobs.sh -q"
    echo "• Check results: ./submit_boltz_jobs.sh -r"
    echo "• List YAML files: ./submit_boltz_jobs.sh -l"
    echo ""
    
    echo -e "${YELLOW}⚠️  Important Notes:${NC}"
    echo "• A100 GPUs have 80GB memory - should handle your predictions easily"
    echo "• Array jobs run max 2 variants simultaneously to be respectful of cluster resources"
    echo "• Results are automatically copied back from local scratch"
    echo "• Always check your job outputs for any errors"
    echo ""
    
    echo -e "${BLUE}🔬 For Your HCM Research:${NC}"
    echo "• Your variants have very high AlphaMissense scores (0.95+)"
    echo "• Boltz-2 predictions will provide valuable structural insights"
    echo "• Consider drug binding site analysis after structure prediction"
    echo "• This could be groundbreaking for therapeutic development!"
}

# Main execution
echo "Starting setup process..."
echo ""

check_cluster
echo ""

setup_directories
echo ""

make_executable
echo ""

setup_conda
echo ""

install_boltz
echo ""

create_aliases
echo ""

echo -e "${YELLOW}Do you want to submit a GPU test job? (y/N):${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_gpu_access
    echo ""
fi

final_instructions 