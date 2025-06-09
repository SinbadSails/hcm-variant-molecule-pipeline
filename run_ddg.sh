#!/usr/bin/env bash
set -euo pipefail

# where the Rosetta MPI binary lives
ROSETTA_BIN=/share/apps/rc/software/Rosetta/3.12-foss-2018b/bin/ddg_monomer.mpi.linuxgccrelease

while IFS=$' \t' read -r CHAIN POS WT MUT; do
  echo "=== Running variant $CHAIN $POS $WT  $MUT ==="

  # write oneline mutation file
  echo "$CHAIN $POS $WT $MUT" > this_mut.txt

  # unique output name
  OUT=score_${CHAIN}${POS}${WT}${MUT}.sc

  # invoke Rosetta
  "$ROSETTA_BIN" \
    -s MYH7_native.pdb \
    -ddg::mut_file this_mut.txt \
    -ddg::iterations 1 \
    -ignore_unrecognized_res true \
    -in::file:fullatom \
    -fa_max_dis 9.0 \
    -out:file:scorefile "$OUT"

done < variants.txt

