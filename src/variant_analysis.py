"""
HCM Variant Analysis Pipeline
Enhanced version of user's excellent foundation code with robust error handling,
modular design, and extended functionality.
"""

import pandas as pd
import numpy as np
import requests
import tempfile
import re
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from Bio.PDB import PDBParser, PDBIO
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Amino acid mappings
THREE_TO_ONE = {
    "Ala": "A", "Cys": "C", "Asp": "D", "Glu": "E", "Phe": "F", "Gly": "G",
    "His": "H", "Ile": "I", "Lys": "K", "Leu": "L", "Met": "M", "Asn": "N",
    "Pro": "P", "Gln": "Q", "Arg": "R", "Ser": "S", "Thr": "T", "Val": "V",
    "Trp": "W", "Tyr": "Y"
}
ONE_TO_THREE = {v: k for k, v in THREE_TO_ONE.items()}

@dataclass
class VariantData:
    """Container for variant analysis results"""
    clinvar_df: pd.DataFrame
    alphafold_plddt: pd.DataFrame
    alphamisense_scores: pd.DataFrame
    rosetta_ddg: Optional[pd.DataFrame] = None
    combined_df: Optional[pd.DataFrame] = None

class MYH7VariantAnalyzer:
    """Comprehensive MYH7 variant analysis pipeline"""
    
    def __init__(self, data_dir: str = "data/variants", results_dir: str = "results"):
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # MYH7 specific identifiers
        self.uniprot_id = "P12883"  # MYH7 UniProt ID
        self.alphafold_id = "Q14896"  # AlphaFold ID for MYH7
        
    def fetch_clinvar_variants(self, force_refresh: bool = False) -> pd.DataFrame:
        """Enhanced ClinVar variant fetching with caching"""
        cache_file = self.data_dir / "clinvar_myh7.csv"
        
        if not force_refresh and cache_file.exists():
            logger.info("Loading cached ClinVar data")
            return pd.read_csv(cache_file)
        
        logger.info("Fetching ClinVar variants for MYH7...")
        try:
            clinvar_url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
            clinvar = pd.read_csv(clinvar_url, sep="\t", compression="gzip", dtype=str)
            
            # Filter for MYH7 missense variants
            mask = (
                (clinvar.GeneSymbol == "MYH7") & 
                clinvar.Type.str.contains("single nucleotide", na=False) &
                clinvar.Name.str.contains(r"\(p\.[A-Za-z]{3}\d+[A-Za-z]{3}\)", na=False)
            )
            
            vars_df = clinvar.loc[mask, ["GeneSymbol", "Type", "Name", "ClinicalSignificance"]].copy()
            
            # Extract protein change information
            vars_df["ProteinChange"] = vars_df["Name"].str.extract(
                r"\(p\.([A-Za-z]{3}\d+[A-Za-z]{3})\)"
            )
            vars_df = vars_df.dropna(subset=["ProteinChange"]).reset_index(drop=True)
            vars_df["Residue"] = vars_df["ProteinChange"].str.extract(r"(\d+)").astype(int)
            
            # Cache results
            vars_df.to_csv(cache_file, index=False)
            logger.info(f"Found {len(vars_df)} MYH7 variants from ClinVar")
            
            return vars_df
            
        except Exception as e:
            logger.error(f"Error fetching ClinVar data: {e}")
            raise
    
    def fetch_alphamisense_scores(self, force_refresh: bool = False) -> pd.DataFrame:
        """Enhanced AlphaMissense score fetching"""
        cache_file = self.data_dir / "alphamisense_myh7.csv"
        
        if not force_refresh and cache_file.exists():
            logger.info("Loading cached AlphaMissense data")
            return pd.read_csv(cache_file)
        
        logger.info("Fetching AlphaMissense scores...")
        try:
            # Download and process AlphaMissense data
            am_url = "https://zenodo.org/record/8208688/files/AlphaMissense_aa_substitutions.tsv.gz"
            
            # Use subprocess to handle the download and filtering more reliably
            temp_file = self.data_dir / "myh7_alphamisense_temp.tsv"
            
            # Download and filter for MYH7 (P12883)
            subprocess.run([
                "bash", "-c", 
                f"curl -s {am_url} | zgrep -P '^#|{self.uniprot_id}\\t' > {temp_file}"
            ], check=True)
            
            # Read the filtered data
            am = pd.read_csv(
                temp_file, sep="\t", comment="#",
                names=["uniprot", "variant", "score", "class"]
            )
            
            # Convert single-letter to three-letter amino acid codes
            am["ProteinChange"] = am["variant"].apply(self._convert_to_three_letter)
            am = am.dropna(subset=["ProteinChange"])[["ProteinChange", "score", "class"]]
            
            # Cache results
            am.to_csv(cache_file, index=False)
            
            # Clean up temp file
            temp_file.unlink(missing_ok=True)
            
            logger.info(f"Retrieved {len(am)} AlphaMissense scores")
            return am
            
        except Exception as e:
            logger.error(f"Error fetching AlphaMissense data: {e}")
            raise
    
    def _convert_to_three_letter(self, variant: str) -> Optional[str]:
        """Convert single-letter variant notation to three-letter"""
        try:
            match = re.match(r"^([A-Z])(\d+)([A-Z])$", variant)
            if match:
                wt, pos, mut = match.groups()
                return f"{ONE_TO_THREE[wt]}{pos}{ONE_TO_THREE[mut]}"
            return None
        except KeyError:
            return None
    
    def extract_alphafold_plddt(self, pdb_file: Optional[str] = None) -> pd.DataFrame:
        """Extract pLDDT scores from AlphaFold structure"""
        if pdb_file is None:
            pdb_file = "MYH7_native.pdb"
        
        cache_file = self.data_dir / "alphafold_plddt.csv"
        
        if cache_file.exists():
            logger.info("Loading cached pLDDT data")
            return pd.read_csv(cache_file)
        
        logger.info("Extracting pLDDT scores from AlphaFold structure...")
        
        if not Path(pdb_file).exists():
            # Download AlphaFold structure
            af_url = f"https://alphafold.ebi.ac.uk/files/AF-{self.alphafold_id}-F1-model_v4.pdb"
            logger.info(f"Downloading AlphaFold structure from {af_url}")
            
            response = requests.get(af_url)
            response.raise_for_status()
            
            with open(pdb_file, 'wb') as f:
                f.write(response.content)
        
        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("MYH7", pdb_file)
            
            records = []
            for model in structure:
                for chain in model:
                    for residue in chain:
                        if residue.id[0] == " ":  # Regular residue
                            ca_atom = next((a for a in residue if a.get_name() == "CA"), None)
                            if ca_atom:
                                records.append({
                                    "Residue": residue.id[1],
                                    "pLDDT": ca_atom.get_bfactor()
                                })
            
            plddt_df = pd.DataFrame(records)
            plddt_df.to_csv(cache_file, index=False)
            
            logger.info(f"Extracted pLDDT for {len(plddt_df)} residues")
            return plddt_df
            
        except Exception as e:
            logger.error(f"Error extracting pLDDT: {e}")
            raise
    
    def run_rosetta_ddg_analysis(self, top_n: int = 20, force_refresh: bool = False) -> pd.DataFrame:
        """Enhanced Rosetta ΔΔG calculations with proper error handling"""
        cache_file = self.results_dir / "rosetta_ddg_results.csv"
        
        if not force_refresh and cache_file.exists():
            logger.info("Loading cached Rosetta ΔΔG data")
            return pd.read_csv(cache_file)
        
        logger.info(f"Running Rosetta ΔΔG analysis for top {top_n} variants...")
        
        # Load combined data to get top variants
        if not hasattr(self, '_combined_df') or self._combined_df is None:
            logger.error("Must combine data first before running Rosetta analysis")
            raise ValueError("Run combine_data() first")
        
        # Get top variants by AlphaMissense score
        top_variants = self._combined_df.nlargest(top_n, "AlphaMissense_score")
        
        # Create mutation file
        mutfile_path = self.data_dir / "top_variants_mutfile.txt"
        self._create_rosetta_mutfile(top_variants, mutfile_path)
        
        # Run Rosetta calculations
        ddg_results = self._run_rosetta_ddg_monomer(mutfile_path)
        
        # Cache results
        ddg_results.to_csv(cache_file, index=False)
        
        return ddg_results
    
    def _create_rosetta_mutfile(self, variants_df: pd.DataFrame, output_file: Path):
        """Create mutation file for Rosetta ddg_monomer"""
        with open(output_file, 'w') as f:
            for _, row in variants_df.iterrows():
                protein_change = row["ProteinChange"]
                wt_aa = protein_change[:3]
                position = protein_change[3:-3]
                mut_aa = protein_change[-3:]
                
                # Convert to single letter
                wt_single = THREE_TO_ONE.get(wt_aa, "X")
                mut_single = THREE_TO_ONE.get(mut_aa, "X")
                
                if wt_single != "X" and mut_single != "X":
                    f.write(f"A {position} {wt_single} {mut_single}\n")
    
    def _run_rosetta_ddg_monomer(self, mutfile_path: Path) -> pd.DataFrame:
        """Run Rosetta ddg_monomer with proper error handling"""
        rosetta_executable = "./ddg_monomer.linuxgccrelease"
        
        if not Path(rosetta_executable).exists():
            logger.error(f"Rosetta executable not found: {rosetta_executable}")
            raise FileNotFoundError("Rosetta ddg_monomer executable not found")
        
        # Make executable
        os.chmod(rosetta_executable, 0o755)
        
        results = []
        
        with open(mutfile_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                parts = line.strip().split()
                if len(parts) != 4:
                    continue
                
                chain, pos, wt, mut = parts
                variant_name = f"{chain}{pos}{wt}{mut}"
                
                logger.info(f"Processing variant {variant_name} ({line_num})")
                
                # Create individual mutation file
                temp_mutfile = self.data_dir / f"temp_mut_{variant_name}.txt"
                with open(temp_mutfile, 'w') as temp_f:
                    temp_f.write(line)
                
                # Fixed Rosetta command options
                cmd = [
                    rosetta_executable,
                    "-s", "MYH7_native.pdb",
                    "-ddg:mutfile", str(temp_mutfile),
                    "-ddg:iterations", "3",
                    "-out:file:scorefile", f"score_{variant_name}.sc",
                    "-ddg:dump_pdbs", "false",
                    "-ignore_unrecognized_res",
                    "-mute", "all"
                ]
                
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=300
                    )
                    
                    if result.returncode == 0:
                        # Parse score file
                        score_file = f"score_{variant_name}.sc"
                        if Path(score_file).exists():
                            ddg_value = self._parse_rosetta_scorefile(score_file)
                            results.append({
                                "ProteinChange": f"{ONE_TO_THREE[wt]}{pos}{ONE_TO_THREE[mut]}",
                                "Rosetta_ddG": ddg_value,
                                "Status": "Success"
                            })
                        else:
                            logger.warning(f"Score file not found for {variant_name}")
                            results.append({
                                "ProteinChange": f"{ONE_TO_THREE[wt]}{pos}{ONE_TO_THREE[mut]}",
                                "Rosetta_ddG": np.nan,
                                "Status": "No output file"
                            })
                    else:
                        logger.error(f"Rosetta failed for {variant_name}: {result.stderr}")
                        results.append({
                            "ProteinChange": f"{ONE_TO_THREE[wt]}{pos}{ONE_TO_THREE[mut]}",
                            "Rosetta_ddG": np.nan,
                            "Status": f"Error: {result.stderr[:100]}"
                        })
                
                except subprocess.TimeoutExpired:
                    logger.error(f"Timeout for variant {variant_name}")
                    results.append({
                        "ProteinChange": f"{ONE_TO_THREE[wt]}{pos}{ONE_TO_THREE[mut]}",
                        "Rosetta_ddG": np.nan,
                        "Status": "Timeout"
                    })
                
                finally:
                    # Cleanup
                    temp_mutfile.unlink(missing_ok=True)
        
        return pd.DataFrame(results)
    
    def _parse_rosetta_scorefile(self, score_file: str) -> float:
        """Parse Rosetta score file to extract ΔΔG"""
        try:
            with open(score_file, 'r') as f:
                lines = f.readlines()
            
            # Find the data line (skip header)
            for line in lines:
                if line.startswith('SCORE:') and 'ddG' in line:
                    parts = line.split()
                    # The ddG value is typically in a specific column
                    # This may need adjustment based on exact Rosetta output format
                    for i, part in enumerate(parts):
                        if part == 'ddG' and i + 1 < len(parts):
                            return float(parts[i + 1])
            
            # Fallback: try to find numeric values
            for line in lines[1:]:  # Skip header
                if not line.startswith('#') and line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            return float(parts[2])  # Assuming ddG is 3rd column
                        except ValueError:
                            continue
            
            return np.nan
            
        except Exception as e:
            logger.error(f"Error parsing score file {score_file}: {e}")
            return np.nan
    
    def combine_data(self) -> pd.DataFrame:
        """Combine all data sources into master dataframe"""
        logger.info("Combining all variant data sources...")
        
        # Fetch all data
        clinvar_df = self.fetch_clinvar_variants()
        alphamisense_df = self.fetch_alphamisense_scores()
        plddt_df = self.extract_alphafold_plddt()
        
        # Start with ClinVar variants
        combined = clinvar_df.copy()
        
        # Merge AlphaMissense scores
        combined = combined.merge(
            alphamisense_df.rename(columns={"score": "AlphaMissense_score", "class": "AlphaMissense_class"}),
            on="ProteinChange", how="left"
        )
        
        # Merge pLDDT scores
        combined = combined.merge(plddt_df, on="Residue", how="left")
        
        # Load existing Rosetta data if available
        rosetta_file = self.results_dir / "rosetta_ddg_results.csv"
        if rosetta_file.exists():
            rosetta_df = pd.read_csv(rosetta_file)
            combined = combined.merge(
                rosetta_df[["ProteinChange", "Rosetta_ddG"]], 
                on="ProteinChange", how="left"
            )
        
        # Store for later use
        self._combined_df = combined
        
        # Save combined dataset
        output_file = self.results_dir / "MYH7_variants_comprehensive.csv"
        combined.to_csv(output_file, index=False)
        
        logger.info(f"Combined dataset saved with {len(combined)} variants")
        return combined
    
    def create_analysis_visualizations(self, data: pd.DataFrame) -> None:
        """Create comprehensive visualization suite"""
        logger.info("Creating analysis visualizations...")
        
        plt.style.use('seaborn-v0_8')
        fig_dir = self.results_dir / "figures"
        fig_dir.mkdir(exist_ok=True)
        
        # 1. AlphaMissense vs pLDDT
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(
            data["pLDDT"], data["AlphaMissense_score"], 
            alpha=0.6, c=data["Residue"], cmap="viridis"
        )
        ax.set_xlabel("AlphaFold Confidence (pLDDT)")
        ax.set_ylabel("AlphaMissense Pathogenicity Score")
        ax.set_title("Structural Confidence vs Pathogenicity")
        plt.colorbar(scatter, label="Residue Position")
        plt.tight_layout()
        plt.savefig(fig_dir / "plddt_vs_alphamisense.png", dpi=300)
        plt.close()
        
        # 2. Rosetta ΔΔG analysis (if available)
        if "Rosetta_ddG" in data.columns and data["Rosetta_ddG"].notna().any():
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # ΔΔG vs AlphaMissense
            mask = data["Rosetta_ddG"].notna()
            ax1.scatter(
                data.loc[mask, "AlphaMissense_score"], 
                data.loc[mask, "Rosetta_ddG"], 
                alpha=0.7
            )
            ax1.set_xlabel("AlphaMissense Score")
            ax1.set_ylabel("Rosetta ΔΔG (REU)")
            ax1.set_title("Pathogenicity vs Structural Stability")
            ax1.grid(True, alpha=0.3)
            
            # ΔΔG vs pLDDT
            ax2.scatter(
                data.loc[mask, "pLDDT"], 
                data.loc[mask, "Rosetta_ddG"], 
                alpha=0.7, c="orange"
            )
            ax2.set_xlabel("pLDDT")
            ax2.set_ylabel("Rosetta ΔΔG (REU)")
            ax2.set_title("Confidence vs Stability Change")
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(fig_dir / "rosetta_analysis.png", dpi=300)
            plt.close()
        
        # 3. Clinical significance distribution
        if "ClinicalSignificance" in data.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Clean up clinical significance categories
            clinical_clean = data["ClinicalSignificance"].fillna("Unknown")
            clinical_counts = clinical_clean.value_counts()
            
            ax.bar(range(len(clinical_counts)), clinical_counts.values)
            ax.set_xticks(range(len(clinical_counts)))
            ax.set_xticklabels(clinical_counts.index, rotation=45, ha='right')
            ax.set_ylabel("Number of Variants")
            ax.set_title("Distribution of Clinical Significance")
            
            plt.tight_layout()
            plt.savefig(fig_dir / "clinical_significance_distribution.png", dpi=300)
            plt.close()
        
        logger.info(f"Visualizations saved to {fig_dir}")
    
    def generate_summary_report(self, data: pd.DataFrame) -> str:
        """Generate comprehensive analysis summary"""
        report = []
        report.append("# MYH7 Variant Analysis Summary Report\n")
        
        # Basic statistics
        report.append(f"## Dataset Overview")
        report.append(f"- Total variants analyzed: {len(data)}")
        report.append(f"- Variants with AlphaMissense scores: {data['AlphaMissense_score'].notna().sum()}")
        report.append(f"- Variants with pLDDT scores: {data['pLDDT'].notna().sum()}")
        
        if "Rosetta_ddG" in data.columns:
            report.append(f"- Variants with Rosetta ΔΔG: {data['Rosetta_ddG'].notna().sum()}")
        
        # Score distributions
        report.append(f"\n## Score Distributions")
        if "AlphaMissense_score" in data.columns:
            am_stats = data["AlphaMissense_score"].describe()
            report.append(f"- AlphaMissense: mean={am_stats['mean']:.3f}, std={am_stats['std']:.3f}")
        
        if "pLDDT" in data.columns:
            plddt_stats = data["pLDDT"].describe()
            report.append(f"- pLDDT: mean={plddt_stats['mean']:.1f}, std={plddt_stats['std']:.1f}")
        
        # Top pathogenic variants
        if "AlphaMissense_score" in data.columns:
            report.append(f"\n## Top 10 Most Pathogenic Variants (AlphaMissense)")
            top_pathogenic = data.nlargest(10, "AlphaMissense_score")
            for _, row in top_pathogenic.iterrows():
                report.append(f"- {row['ProteinChange']}: {row['AlphaMissense_score']:.3f}")
        
        # Correlations
        if "Rosetta_ddG" in data.columns and data["Rosetta_ddG"].notna().sum() > 5:
            corr = data["AlphaMissense_score"].corr(data["Rosetta_ddG"])
            report.append(f"\n## Correlations")
            report.append(f"- AlphaMissense vs Rosetta ΔΔG: r={corr:.3f}")
        
        report_text = "\n".join(report)
        
        # Save report
        report_file = self.results_dir / "analysis_summary_report.md"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        logger.info(f"Summary report saved to {report_file}")
        return report_text

def main():
    """Main analysis pipeline"""
    analyzer = MYH7VariantAnalyzer()
    
    # Run complete analysis
    combined_data = analyzer.combine_data()
    
    # Create visualizations
    analyzer.create_analysis_visualizations(combined_data)
    
    # Generate summary report
    report = analyzer.generate_summary_report(combined_data)
    print(report)
    
    # Optionally run Rosetta analysis for top variants
    print("\nRun Rosetta ΔΔG analysis for top 20 variants? (y/n): ", end="")
    if input().lower().startswith('y'):
        rosetta_results = analyzer.run_rosetta_ddg_analysis(top_n=20)
        print(f"Rosetta analysis complete. Results: {len(rosetta_results)} variants processed")
        
        # Re-combine with Rosetta results and update visualizations
        updated_data = analyzer.combine_data()
        analyzer.create_analysis_visualizations(updated_data)
        analyzer.generate_summary_report(updated_data)

if __name__ == "__main__":
    main() 