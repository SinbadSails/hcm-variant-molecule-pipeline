#!/usr/bin/env python3
"""Download pinned public inputs temporarily and write a small provenance report."""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

from audit import audit_files


REPOSITORY = "SinbadSails/hcm-variant-molecule-pipeline"
COMMIT = "17686a4ba92229828f2f527ac0e3a8d408bf8751"
RAW_BASE = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}"


def download(url):
    request = Request(url, headers={"User-Agent": "myh7-provenance-check/1"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("report.json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="myh7-provenance-") as temporary:
        inputs = Path(temporary)
        for name in ("MYH7_native.pdb", "MYH7_variants_final_annotated.csv"):
            (inputs / name).write_bytes(download(f"{RAW_BASE}/{name}"))
        report = audit_files(inputs / "MYH7_native.pdb",
                             inputs / "MYH7_variants_final_annotated.csv")
        report["repository"] = REPOSITORY
        report["commit"] = COMMIT
        for key in ("pdb_source", "csv_source"):
            name = report[key]["filename"]
            report[key]["url"] = f"{RAW_BASE}/{name}"
            report[key]["browser_url"] = (
                f"https://github.com/{REPOSITORY}/blob/{COMMIT}/{name}")
        report["official_uniprot_confirmations"] = []
        for accession in ("P12883", "Q14896"):
            url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
            data = download(url)
            entry = json.loads(data)
            report["official_uniprot_confirmations"].append({
                "accession": entry["primaryAccession"],
                "entry_name": entry["uniProtkbId"],
                "recommended_protein_name": entry["proteinDescription"][
                    "recommendedName"]["fullName"]["value"],
                "gene_names": [g["geneName"]["value"] for g in entry["genes"]
                               if "geneName" in g],
                "entry_audit": entry["entryAudit"],
                "url": url,
                "entry_url": f"https://www.uniprot.org/uniprotkb/{accession}/entry",
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "version_note": (
                    "UniProt endpoints are live; entry versions and hashes record "
                    "the response used here and may change on a later run."),
            })
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output}: metadata "
          f"{report['pdb_metadata_check']['status']}; "
          f"{report['variant_csv_check']['rows']} CSV rows")


if __name__ == "__main__":
    main()
