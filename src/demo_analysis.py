#!/usr/bin/env python3
"""
MYH7 Variant Analysis Demo Script
Demonstrates the enhanced pipeline functionality
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

def main():
    """Main demonstration function"""
    print("🚀 MYH7 Variant Analysis Pipeline Demo")
    print("="*50)
    
    # Load existing dataset if available
    data_file = "MYH7_variants_final_annotated.csv"
    
    if Path(data_file).exists():
        print(f"📁 Loading dataset: {data_file}")
        df = pd.read_csv(data_file)
        
        print(f"✅ Loaded {len(df)} variants")
        print(f"📊 Columns: {list(df.columns)}")
        
        # Basic analysis
        if 'AlphaMissense' in df.columns:
            am_stats = df['AlphaMissense'].describe()
            print(f"\n🧬 AlphaMissense Statistics:")
            print(f"   Mean: {am_stats['mean']:.3f}")
            print(f"   Std:  {am_stats['std']:.3f}")
            print(f"   Range: [{am_stats['min']:.3f}, {am_stats['max']:.3f}]")
            
            # High pathogenicity variants
            high_path = df[df['AlphaMissense'] > 0.8]
            print(f"   High pathogenicity (>0.8): {len(high_path)} variants")
        
        if 'Rosetta_ddG' in df.columns:
            ddg_mask = df['Rosetta_ddG'].notna()
            if ddg_mask.any():
                ddg_stats = df.loc[ddg_mask, 'Rosetta_ddG'].describe()
                print(f"\n⚖️ Rosetta ΔΔG Statistics:")
                print(f"   Mean: {ddg_stats['mean']:.3f} REU")
                print(f"   Std:  {ddg_stats['std']:.3f} REU")
                print(f"   Range: [{ddg_stats['min']:.3f}, {ddg_stats['max']:.3f}] REU")
                
                # Stability analysis
                destabilizing = df[df['Rosetta_ddG'] > 1.0]
                stabilizing = df[df['Rosetta_ddG'] < -1.0]
                print(f"   Destabilizing (>1 REU): {len(destabilizing)} variants")
                print(f"   Stabilizing (<-1 REU): {len(stabilizing)} variants")
        
        if 'pLDDT' in df.columns:
            plddt_stats = df['pLDDT'].describe()
            print(f"\n🏗️ pLDDT Confidence Statistics:")
            print(f"   Mean: {plddt_stats['mean']:.1f}")
            print(f"   High confidence (>90): {(df['pLDDT'] > 90).sum()} variants")
            print(f"   Low confidence (<50): {(df['pLDDT'] < 50).sum()} variants")
        
        # Correlations
        if all(col in df.columns for col in ['AlphaMissense', 'Rosetta_ddG']):
            corr = df['AlphaMissense'].corr(df['Rosetta_ddG'])
            print(f"\n🔗 Key Correlation:")
            print(f"   AlphaMissense vs Rosetta ΔΔG: r = {corr:.3f}")
        
        # Top variants for research focus
        if 'AlphaMissense' in df.columns:
            print(f"\n🎯 TOP 5 RESEARCH TARGETS:")
            top_variants = df.nlargest(5, 'AlphaMissense')
            for i, (_, row) in enumerate(top_variants.iterrows(), 1):
                variant = row.get('ProteinChange', 'N/A')
                am_score = row.get('AlphaMissense', 0)
                ddg = row.get('Rosetta_ddG', np.nan)
                ddg_str = f"{ddg:.2f}" if pd.notna(ddg) else "pending"
                print(f"   {i}. {variant}: AlphaMissense={am_score:.3f}, ΔΔG={ddg_str}")
        
        print(f"\n✅ Analysis complete! Dataset ready for advanced research.")
        
    else:
        print(f"❌ Dataset not found: {data_file}")
        print("Please run the Jupyter notebook to generate the data first.")
    
    # Show available tools
    print(f"\n🔧 AVAILABLE TOOLS:")
    print("   1. notebooks/1_MYH7_variant_analysis.ipynb - Main analysis pipeline")
    print("   2. notebooks/2_molecular_modeling.ipynb - Small molecule analysis")
    print("   3. run_rosetta_fixed.sh - Fixed Rosetta ΔΔG calculations")
    print("   4. src/demo_analysis.py - This demo script")
    
    print(f"\n🚀 NEXT STEPS:")
    print("   1. cd notebooks && jupyter lab 1_MYH7_variant_analysis.ipynb")
    print("   2. Run all cells to generate comprehensive analysis")
    print("   3. Execute: bash run_rosetta_fixed.sh (if needed)")
    print("   4. Explore molecular modeling in notebook 2")

if __name__ == "__main__":
    main() 