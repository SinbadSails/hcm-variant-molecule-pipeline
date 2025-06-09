#!/bin/bash

# =============================================================================
# HCM VARIANT SUBMISSION PIPELINE
# Submit high-priority variants for structure prediction
# =============================================================================

echo "🚀 HCM VARIANT STRUCTURE PREDICTION SUBMISSION"
echo "Started: $(date)"

# Create directories
mkdir -p {results,failures,cluster_logs}

# Initialize prediction log
echo "Status,Variant,JobID,Timestamp,Runtime/ExitCode" > prediction_log.csv

# High-priority variants for publication
VARIANTS=(
    "variant_gly584arg.yaml"
    "variant_arg249gln.yaml"
    "domain_variant_gly584arg.yaml"
    "myh7_gly584arg.yaml"
)

echo ""
echo "📋 Submitting ${#VARIANTS[@]} high-priority HCM variants:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

JOB_IDS=()

for variant in "${VARIANTS[@]}"; do
    if [ -f "$variant" ]; then
        echo "  ✅ Submitting: $variant"
        JOB_ID=$(sbatch --parsable boltz_production.job "$variant")
        if [ $? -eq 0 ]; then
            JOB_IDS+=($JOB_ID)
            echo "     Job ID: $JOB_ID"
        else
            echo "     ❌ Submission failed"
        fi
    else
        echo "  ❌ File not found: $variant"
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ${#JOB_IDS[@]} -gt 0 ]; then
    echo "🎯 SUBMISSION SUMMARY:"
    echo "   Submitted jobs: ${#JOB_IDS[@]}"
    echo "   Job IDs: ${JOB_IDS[*]}"
    echo ""
    echo "📊 MONITORING COMMANDS:"
    echo "   Check status: squeue -u $USER"
    echo "   Watch progress: watch -n 30 'squeue -u $USER'"
    echo "   View logs: tail -f cluster_logs/hcm_*.out"
    echo ""
    echo "📁 RESULTS LOCATION:"
    echo "   Success: results/"
    echo "   Failures: failures/"
    echo "   Logs: cluster_logs/"
    echo ""
    echo "🎯 EXPECTED TIMELINE:"
    echo "   Single job: ~30-90 minutes"
    echo "   All variants: ~2-6 hours"
    echo "   Publication ready: Tomorrow!"
    echo ""
    echo "📝 NEXT STEPS:"
    echo "   1. Monitor job completion"
    echo "   2. Validate structure quality"
    echo "   3. Draft methodology paper"
    echo "   4. Submit to bioRxiv"
    echo ""
    echo "🚀 Building the billion-dollar empire starts NOW!"
else
    echo "❌ No jobs were submitted successfully"
    echo "Check file paths and cluster permissions"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 