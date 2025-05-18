# HCM Variant & Molecule Pipeline

This repository contains two parallel pipelines:

1. **Variant Analysis (MYH7)**  
   - Retrieve ClinVar missense variants  
   - Pathogenicity scoring via AlphaMissense (VarCards API)  
   - Structural mapping (AlphaFold2 models)  
   - ΔΔG estimation (Rosetta)

2. **Small Molecule Modeling**  
   - QM9 dataset via DeepChem  
   - Molecular featurization (GraphConv, RDKit descriptors)  
   - Graph Neural Network model training and evaluation

## Repo Structure

- `data/` – raw and processed input data  
- `notebooks/` – Jupyter notebooks (analysis workflows)  
- `src/` – reusable Python modules (if needed)  
- `results/` – figures, tables, model outputs  
- `docs/` – preprint outline and bibliography  
- `environment.yml` – conda environment specification  

## Quick Start

1. Clone the repo:  
   ```bash
   git clone https://github.com/your-username/hcm-variant-molecule-pipeline.git
   cd hcm-variant-molecule-pipeline

2. conda env create -f environment.yml
    conda activate hcm-pipeline

3. jupyter lab notebooks/1_variant_analysis_MYH7.ipynb



