#!/usr/bin/env python3
"""
🧬 MYH7 Variant Analysis - Main Execution Script
Streamlined pipeline for publication-ready results
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

def main():
    """Execute complete MYH7 variant analysis pipeline"""
    
    print("🚀 MYH7 VARIANT ANALYSIS PIPELINE")
    print("="*50)
    print("🎯 Goal: Publication-ready analysis for cardiac surgery residency")
    print("💰 Vision: Foundation for billion-dollar drug discovery company")
    print("🔬 Focus: Precision medicine in hypertrophic cardiomyopathy")
    print()
    
    # Setup paths
    results_dir = Path("results")
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Load master dataset
    data_file = "MYH7_variants_final_annotated.csv"
    print(f"📁 Loading master dataset: {data_file}")
    
    if not Path(data_file).exists():
        print(f"❌ ERROR: {data_file} not found!")
        print("Please ensure the dataset is in the root directory")
        return False
    
    df = pd.read_csv(data_file)
    print(f"✅ Loaded {len(df):,} MYH7 variants")
    
    # Data quality assessment
    print(f"\n📊 DATASET QUALITY ASSESSMENT")
    print(f"   Columns: {list(df.columns)}")
    
    key_columns = ['ProteinChange', 'AlphaMissense', 'Rosetta_ddG', 'pLDDT', 'Residue']
    available_columns = [col for col in key_columns if col in df.columns]
    print(f"   Key columns available: {available_columns}")
    
    # Calculate completeness
    for col in available_columns:
        if col in df.columns:
            completeness = (df[col].notna().sum() / len(df)) * 100
            print(f"   {col}: {completeness:.1f}% complete")
    
    # Generate core analysis
    print(f"\n🔬 CORE SCIENTIFIC ANALYSIS")
    
    # 1. Pathogenicity analysis
    if 'AlphaMissense' in df.columns:
        am_stats = df['AlphaMissense'].describe()
        high_pathogenic = df[df['AlphaMissense'] > 0.8]
        
        print(f"   🧬 AlphaMissense Pathogenicity:")
        print(f"      Mean score: {am_stats['mean']:.3f}")
        print(f"      High pathogenicity (>0.8): {len(high_pathogenic)} variants ({len(high_pathogenic)/len(df)*100:.1f}%)")
        
        # Top 10 most pathogenic
        top_pathogenic = df.nlargest(10, 'AlphaMissense')
        print(f"      Top 10 most pathogenic variants:")
        for i, (_, row) in enumerate(top_pathogenic.iterrows(), 1):
            variant = row.get('ProteinChange', 'N/A')
            score = row.get('AlphaMissense', 0)
            print(f"        {i:2d}. {variant}: {score:.3f}")
    
    # 2. Structural analysis
    if 'pLDDT' in df.columns:
        plddt_stats = df['pLDDT'].describe()
        high_conf = df[df['pLDDT'] > 90]
        low_conf = df[df['pLDDT'] < 50]
        
        print(f"   🏗️ Structural Confidence (pLDDT):")
        print(f"      Mean confidence: {plddt_stats['mean']:.1f}")
        print(f"      High confidence (>90): {len(high_conf)} variants")
        print(f"      Low confidence (<50): {len(low_conf)} variants")
    
    # 3. Stability analysis  
    if 'Rosetta_ddG' in df.columns:
        ddg_mask = df['Rosetta_ddG'].notna()
        if ddg_mask.any():
            ddg_stats = df.loc[ddg_mask, 'Rosetta_ddG'].describe()
            destabilizing = df[df['Rosetta_ddG'] > 1.0]
            stabilizing = df[df['Rosetta_ddG'] < -1.0]
            
            print(f"   ⚖️ Protein Stability (Rosetta ΔΔG):")
            print(f"      Mean ΔΔG: {ddg_stats['mean']:.3f} REU")
            print(f"      Destabilizing (>1 REU): {len(destabilizing)} variants")
            print(f"      Stabilizing (<-1 REU): {len(stabilizing)} variants")
    
    # 4. Key correlations
    if all(col in df.columns for col in ['AlphaMissense', 'Rosetta_ddG']):
        corr = df['AlphaMissense'].corr(df['Rosetta_ddG'])
        print(f"   🔗 Key Finding:")
        print(f"      AlphaMissense vs ΔΔG correlation: r = {corr:.3f}")
    
    # Generate publication-quality figure
    print(f"\n📊 GENERATING PUBLICATION FIGURES")
    
    plt.style.use('seaborn-v0_8')
    fig = plt.figure(figsize=(16, 12))
    
    # Main correlation plot
    ax1 = plt.subplot(2, 3, 1)
    if all(col in df.columns for col in ['AlphaMissense', 'Rosetta_ddG']):
        mask = df['AlphaMissense'].notna() & df['Rosetta_ddG'].notna()
        plt.scatter(df.loc[mask, 'AlphaMissense'], df.loc[mask, 'Rosetta_ddG'], 
                   alpha=0.6, s=30, c='steelblue')
        plt.xlabel('AlphaMissense Pathogenicity Score', fontsize=12)
        plt.ylabel('Rosetta ΔΔG (REU)', fontsize=12)
        plt.title('🎯 Pathogenicity vs Structural Stability', fontsize=14, fontweight='bold')
        
        corr = df['AlphaMissense'].corr(df['Rosetta_ddG'])
        plt.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax1.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        plt.grid(True, alpha=0.3)
    
    # Pathogenicity distribution
    ax2 = plt.subplot(2, 3, 2)
    if 'AlphaMissense' in df.columns:
        df['AlphaMissense'].hist(bins=40, alpha=0.7, color='coral', edgecolor='black')
        plt.axvline(df['AlphaMissense'].mean(), color='darkred', linestyle='--', linewidth=2)
        plt.axvline(0.8, color='red', linestyle=':', linewidth=3, label='High pathogenicity')
        plt.xlabel('AlphaMissense Score', fontsize=12)
        plt.ylabel('Number of Variants', fontsize=12)
        plt.title('🧬 Pathogenicity Distribution', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    # Stability distribution  
    ax3 = plt.subplot(2, 3, 3)
    if 'Rosetta_ddG' in df.columns:
        mask = df['Rosetta_ddG'].notna()
        df.loc[mask, 'Rosetta_ddG'].hist(bins=30, alpha=0.7, color='orange', edgecolor='black')
        plt.axvline(0, color='red', linestyle='-', linewidth=3, label='Neutral')
        plt.axvline(1, color='darkred', linestyle='--', label='Destabilizing')
        plt.axvline(-1, color='blue', linestyle='--', label='Stabilizing')
        plt.xlabel('Rosetta ΔΔG (REU)', fontsize=12)
        plt.ylabel('Number of Variants', fontsize=12)
        plt.title('⚖️ Stability Changes', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    # Confidence vs Pathogenicity
    ax4 = plt.subplot(2, 3, 4)
    if all(col in df.columns for col in ['pLDDT', 'AlphaMissense', 'Residue']):
        scatter = plt.scatter(df['pLDDT'], df['AlphaMissense'], 
                            alpha=0.6, c=df['Residue'], cmap='viridis', s=25)
        plt.xlabel('AlphaFold Confidence (pLDDT)', fontsize=12)
        plt.ylabel('AlphaMissense Score', fontsize=12)
        plt.title('🗺️ Confidence vs Pathogenicity', fontsize=14, fontweight='bold')
        plt.colorbar(scatter, label='Residue Position')
        plt.axhline(0.8, color='red', linestyle=':', alpha=0.7)
        plt.axvline(90, color='red', linestyle=':', alpha=0.7)
        plt.grid(True, alpha=0.3)
    
    # High-impact variants
    ax5 = plt.subplot(2, 3, 5)
    if all(col in df.columns for col in ['AlphaMissense', 'Rosetta_ddG']):
        high_path = df['AlphaMissense'] > 0.8
        destabilizing = df['Rosetta_ddG'] > 1.0
        
        colors = ['lightgray' if not (hp and dest) else 'red' 
                 for hp, dest in zip(high_path, destabilizing)]
        
        plt.scatter(df['AlphaMissense'], df['Rosetta_ddG'], c=colors, alpha=0.7, s=25)
        plt.xlabel('AlphaMissense Score', fontsize=12)
        plt.ylabel('Rosetta ΔΔG (REU)', fontsize=12)
        plt.title('🚨 High-Impact Variants', fontsize=14, fontweight='bold')
        plt.axhline(1.0, color='red', linestyle='--', alpha=0.7)
        plt.axvline(0.8, color='red', linestyle='--', alpha=0.7)
        plt.grid(True, alpha=0.3)
        
        high_impact = (high_path & destabilizing).sum()
        plt.text(0.05, 0.95, f'High-impact: {high_impact}', transform=ax5.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Sequence analysis
    ax6 = plt.subplot(2, 3, 6)
    if all(col in df.columns for col in ['Residue', 'AlphaMissense']):
        plt.scatter(df['Residue'], df['AlphaMissense'], alpha=0.5, s=15, c='purple')
        plt.xlabel('Residue Position', fontsize=12)
        plt.ylabel('AlphaMissense Score', fontsize=12)
        plt.title('🧪 Pathogenicity Along Sequence', fontsize=14, fontweight='bold')
        plt.axhline(0.8, color='red', linestyle='--', alpha=0.7)
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    figure_file = figures_dir / "MYH7_comprehensive_analysis.png"
    plt.savefig(figure_file, dpi=300, bbox_inches='tight')
    print(f"✅ Publication figure saved: {figure_file}")
    plt.show()
    
    # Generate research priorities
    print(f"\n🎯 RESEARCH PRIORITIES FOR PUBLICATIONS")
    
    if 'AlphaMissense' in df.columns:
        # Identify top research targets
        top_variants = df.nlargest(20, 'AlphaMissense')
        
        print(f"   📋 Top 20 variants for experimental validation:")
        for i, (_, row) in enumerate(top_variants.iterrows(), 1):
            variant = row.get('ProteinChange', 'N/A')
            am_score = row.get('AlphaMissense', 0)
            ddg = row.get('Rosetta_ddG', np.nan)
            plddt = row.get('pLDDT', np.nan)
            
            ddg_str = f"ΔΔG={ddg:.2f}" if pd.notna(ddg) else "ΔΔG=pending"
            plddt_str = f"pLDDT={plddt:.1f}" if pd.notna(plddt) else "pLDDT=N/A"
            
            print(f"     {i:2d}. {variant}: AM={am_score:.3f}, {ddg_str}, {plddt_str}")
        
        # Save top variants for Rosetta/Desmond analysis
        top_variants_file = results_dir / "top_20_research_targets.csv"
        top_variants.to_csv(top_variants_file, index=False)
        print(f"   💾 Research targets saved: {top_variants_file}")
    
    # Generate summary for publications
    print(f"\n📚 PUBLICATION READINESS SUMMARY")
    print(f"   ✅ Dataset: {len(df):,} variants analyzed")
    print(f"   ✅ Figures: Publication-quality visualization generated")
    print(f"   ✅ Statistics: Key correlations calculated")
    print(f"   ✅ Targets: Top variants identified for follow-up")
    
    print(f"\n🚀 NEXT STEPS FOR RESIDENCY APPLICATIONS")
    print(f"   1. Submit preprint to bioRxiv (immediate)")
    print(f"   2. Run Rosetta ΔΔG on top 20 variants")  
    print(f"   3. Prepare Desmond MD simulations (Phase 2)")
    print(f"   4. Write first manuscript draft")
    print(f"   5. Apply to cardiac surgery programs with 'under review' status")
    
    print(f"\n💰 COMMERCIAL DEVELOPMENT ROADMAP")
    print(f"   Phase 1: Academic validation & publication")
    print(f"   Phase 2: Desmond MD validation + industry partnerships")
    print(f"   Phase 3: Drug screening + startup formation")
    print(f"   Phase 4: Clinical trials + billion-dollar exit")
    
    print(f"\n🎉 ANALYSIS COMPLETE! Ready for world-class research! 🎉")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 Pipeline executed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Pipeline failed. Check errors above.")
        sys.exit(1) 