import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from audit import check_pdb_metadata, check_variant_csv


class ProvenanceAuditTests(unittest.TestCase):
    def test_pdb_metadata_and_cli_detect_wrong_accession(self):
        with tempfile.TemporaryDirectory() as folder:
            pdb = Path(folder) / "candidate.pdb"
            pdb.write_text(
                "TITLE     ALPHAFOLD PREDICTION FOR CARDIAC MYBPC3 (Q14896)\n"
                "DBREF  TEST A    1    5  UNP    Q14896   MYPC3_HUMAN\n",
                encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("audit.py")),
                 "--pdb", str(pdb)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["pdb_metadata_check"]["status"], "mismatch")
            self.assertEqual(report["pdb_metadata_check"]["observed_accessions"],
                             ["Q14896"])
            pdb.write_text("AFID   AF-P12883-F1\n", encoding="utf-8")
            self.assertEqual(check_pdb_metadata(pdb)["status"], "match")
            pdb.write_text("TITLE     UNKNOWN STRUCTURE\n", encoding="utf-8")
            self.assertEqual(check_pdb_metadata(pdb)["status"], "unavailable")

    def test_csv_distinguishes_replicate_ambiguity_and_equal_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            table = Path(folder) / "variants.csv"
            table.write_text(
                "ProteinChange,Rosetta_ddG\n"
                "Arg403Gln,-2.17\nArg403Gln,1.99\n"
                "Arg249Gln,1.00\nArg249Gln,1\n"
                ",\nVal1Ala,not-a-number\n", encoding="utf-8")
            report = check_variant_csv(table)
            self.assertEqual(report["rows"], 6)
            self.assertEqual(report["distinct_nonblank_protein_changes"], 3)
            self.assertEqual(report["rows_with_blank_protein_change"], 1)
            self.assertEqual(report["rows_with_missing_ddg"], 1)
            self.assertEqual(report["rows_with_invalid_ddg"], 1)
            self.assertEqual(
                report["protein_changes_with_multiple_distinct_ddg_values"], 1)
            self.assertEqual(report["examples"], [{
                "protein_change": "Arg403Gln",
                "distinct_ddg_values": ["-2.17", "1.99"]}])
            self.assertIn("not proof", report["interpretation"])


if __name__ == "__main__":
    unittest.main()
