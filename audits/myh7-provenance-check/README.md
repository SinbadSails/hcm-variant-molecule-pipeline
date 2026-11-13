# MYH7 provenance check

A small, standard-library Python audit of accession metadata and variant-table
provenance signals. It does **not** verify protein sequences, validate simulation
physics, or establish clinical or commercial findings.

## Inspect your own inputs

```sh
python3 audit.py --pdb path/to/structure.pdb --csv path/to/variants.csv --output local-report.json
```

`--csv` is optional. The expected UniProt accession defaults to **P12883** (MYH7)
and can be changed with `--expected-uniprot`. The PDB check reads accession strings
in TITLE, DBREF/DBREF1/DBREF2, AFID, and AFID/AF-prefixed REMARK records. It does
not infer identity from the filename or align residues. Exit codes: **0** metadata
matches, **1** metadata mismatch, **2** missing accession metadata or input error.
A mismatch still writes the JSON report.

The CSV check requires `ProteinChange` and `Rosetta_ddG` columns. It counts rows,
nonblank protein changes and missing/invalid scores. Numerically equal score
representations (for example, `1` and `1.00`) count as one value. Multiple distinct
ddG values for a protein change are reported as **provenance ambiguity**: replicates,
structures or protocols may legitimately differ. The report includes at most ten
examples; its ambiguity count covers the whole table.

## Reproduce the public-repository report

```sh
python3 reproduce.py --output report.json
python3 -m unittest -v
```

Python 3.9+; no third-party packages. Reproduction downloads two public files from
`SinbadSails/hcm-variant-molecule-pipeline`, pinned to commit
`17686a4ba92229828f2f527ac0e3a8d408bf8751`, into a temporary directory that is
removed automatically. It also fetches the two official UniProt JSON records.
The checked-in `report.json` records exact source URLs, SHA-256 hashes, byte counts,
and UniProt entry versions. Large input structures and tables are not bundled.
The reproduction command exits successfully when the report is written, including
when the report identifies a metadata mismatch.

The pinned PDB declares **Q14896**. Official UniProt records identify
[Q14896 as MYBPC3](https://www.uniprot.org/uniprotkb/Q14896/entry),
myosin-binding protein C, cardiac-type, and
[P12883 as MYH7](https://www.uniprot.org/uniprotkb/P12883/entry), myosin-7.
That is a concrete metadata discrepancy requiring investigation before MYH7
structure-derived results can be interpreted. It is not a sequence verification.
UniProt endpoints are live and may produce newer response versions/hashes on
later runs; the GitHub inputs remain pinned.

The two fixture tests cover metadata mismatch/match/unavailable behavior and
the distinction between multiple-score ambiguity and equivalent numeric scores.
