#!/usr/bin/env python3
"""Inspect PDB accession metadata and optional variant-table provenance signals."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re


ACCESSION = re.compile(
    r"(?<![A-Z0-9])(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|"
    r"[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(?![A-Z0-9])"
)
MISSING = {"", "na", "n/a", "nan", "none", "null"}


def file_record(path):
    path = Path(path)
    data = path.read_bytes()
    return {"filename": path.name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def check_pdb_metadata(path, expected="P12883"):
    """Check declared accessions only; no residue/sequence identity assertion."""
    records = []
    observed = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            record_type = line[:6].strip()
            if (record_type in {"TITLE", "DBREF", "DBREF1", "DBREF2", "AFID"}
                    or (record_type == "REMARK" and
                        ("AFID" in line or "AF-" in line))):
                accessions = sorted(set(ACCESSION.findall(line)))
                observed.update(accessions)
                records.append({"line": line_number, "record_type": record_type,
                                "text": line, "accessions": accessions})
    status = ("unavailable" if not observed else
              "match" if observed == {expected} else "mismatch")
    return {
        "expected_uniprot": expected,
        "observed_accessions": sorted(observed),
        "status": status,
        "scope": "Metadata accession check only; sequence identity is not verified.",
        "metadata_records": records,
    }


def check_variant_csv(path, example_limit=10):
    """Describe duplicate score provenance without assuming replicates are invalid."""
    row_count = blank_changes = missing_ddg = invalid_ddg = 0
    changes = set()
    ddg_values = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ProteinChange", "Rosetta_ddG"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires ProteinChange and Rosetta_ddG columns")
        for row in reader:
            row_count += 1
            if None in row:
                raise ValueError(f"CSV row {reader.line_num} has extra columns")
            change = (row["ProteinChange"] or "").strip()
            if change:
                changes.add(change)
            else:
                blank_changes += 1
            raw_score = (row["Rosetta_ddG"] or "").strip()
            if raw_score.lower() in MISSING:
                missing_ddg += 1
                continue
            try:
                score = Decimal(raw_score)
                if not score.is_finite():
                    raise InvalidOperation
            except InvalidOperation:
                invalid_ddg += 1
                continue
            if change:
                ddg_values.setdefault(change, set()).add(score)
    ambiguous = {k: v for k, v in ddg_values.items() if len(v) > 1}
    examples = [
        {"protein_change": change,
         "distinct_ddg_values": [str(v.normalize()) for v in sorted(values)]}
        for change, values in sorted(ambiguous.items())[:example_limit]
    ]
    return {
        "rows": row_count,
        "distinct_nonblank_protein_changes": len(changes),
        "rows_with_blank_protein_change": blank_changes,
        "rows_with_missing_ddg": missing_ddg,
        "rows_with_invalid_ddg": invalid_ddg,
        "protein_changes_with_multiple_distinct_ddg_values": len(ambiguous),
        "examples": examples,
        "examples_limit": example_limit,
        "interpretation": (
            "Multiple distinct ddG values for a protein change are provenance "
            "ambiguities, not proof of invalid scores. Replicates, structures or "
            "protocols may differ; raw outputs and run metadata are needed."
        ),
    }


def audit_files(pdb_path, csv_path=None, expected="P12883"):
    report = {
        "schema_version": 1,
        "pdb_source": file_record(pdb_path),
        "pdb_metadata_check": check_pdb_metadata(pdb_path, expected),
        "limits": [
            "No sequence alignment or residue-mapping verification is performed.",
            "No simulation is executed or assessed for physical validity.",
            "No clinical, mechanistic or commercial conclusions are established.",
        ],
    }
    if csv_path is not None:
        report["csv_source"] = file_record(csv_path)
        report["variant_csv_check"] = check_variant_csv(csv_path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdb", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--expected-uniprot", default="P12883")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    expected = args.expected_uniprot.strip().upper()
    if not ACCESSION.fullmatch(expected):
        parser.error("--expected-uniprot must be a UniProt accession")
    try:
        report = audit_files(args.pdb, args.csv, expected)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        parser.exit(2, f"audit error: {exc}\n")
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return {"match": 0, "mismatch": 1, "unavailable": 2}[
        report["pdb_metadata_check"]["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
