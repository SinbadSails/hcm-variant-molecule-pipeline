#!/usr/bin/env python3
"""Validate an exported demo without running molecular dynamics.

Uses Horn's quaternion eigenvalue method independently of the generator's
Kabsch SVD, checks units/times/dimensions/finite values and recorded digests,
and exercises the generator's alignment on synthetic rigid transforms.
The source PDB is verified only when --pdb is supplied; otherwise that check
is explicitly reported as not_checked. Requires NumPy, but not OpenMM.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import numpy as np


BUNDLED_DEMO_SHA256 = "2c23e2b07fd9e296e19b0a5ef27304b886fc120146532401a5c8a4b992ecaa91"
BUNDLED_HISTORICAL_COMMAND = (
    "/tmp/cheaha-openmm-venv/bin/python "
    "/workspace/projects/protein-motion-lab/scripts/generate_demo.py "
    "--pdb /workspace/cheaha/inputs/1UBQ.pdb "
    "--output /workspace/projects/protein-motion-lab/data/demo.json "
    "--seed 1001 --threads 2 --minimize-iterations 200 "
    "--equilibration-steps 200 --production-steps 1000 "
    "--sample-every-steps 20 --max-wall-seconds 120"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def horn_rmsd(a, b):
    """Minimum RMSD from a 4x4 quaternion eigenproblem; no 3x3 SVD."""
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    xx, xy, xz, yx, yy, yz, zx, zy, zz = (a.T @ b).ravel()
    q = np.array([
        [xx + yy + zz, yz - zy, zx - xz, xy - yx],
        [yz - zy, xx - yy - zz, xy + yx, zx + xz],
        [zx - xz, xy + yx, -xx + yy - zz, yz + zy],
        [xy - yx, zx + xz, yz + zy, -xx - yy + zz],
    ])
    energy = np.square(a).sum() + np.square(b).sum()
    return float(np.sqrt(max(0.0, (energy - 2 * np.linalg.eigvalsh(q)[-1]) / len(a))))


def validate(args):
    payload = json.loads(args.data.read_text())
    meta, residues, frames = payload["metadata"], payload["residues"], payload["frames"]
    require(len(residues) > 0 and len(frames) >= 2, "Need residues and at least two frames")
    coordinates = np.asarray([f["positions_angstrom"] for f in frames], dtype=float)
    times = np.asarray([f["time_ps"] for f in frames], dtype=float)
    recorded = np.asarray([f["rmsd_angstrom"] for f in frames], dtype=float)
    require(coordinates.shape == (len(frames), len(residues), 3), "Incorrect coordinate dimensions")
    require(len({r["id"] for r in residues}) == len(residues), "Duplicate residue identifiers")
    require(all(isinstance(r["name"], str) and r["name"] for r in residues), "Invalid residue names")
    require(np.isfinite(coordinates).all() and np.isfinite(times).all() and
            np.isfinite(recorded).all(), "Non-finite coordinates, times or RMSDs")
    require(np.all(recorded >= 0), "Negative RMSD")
    require(all(math.isfinite(f["potential_kj_mol"]) for f in frames
                if "potential_kj_mol" in f), "Non-finite potential energy")
    require(np.all(np.diff(times) > 0), "Frame times must increase strictly")
    require(meta["frame_count"] == len(frames), "Frame-count metadata mismatch")
    require(meta["ca_atom_count"] == len(residues), "C-alpha count metadata mismatch")
    require(meta["position_units"] == "angstrom" and meta["rmsd_units"] == "angstrom"
            and meta["time_units"] == "picosecond", "Unexpected units")
    duration = meta["production_steps_completed"] * meta["timestep_fs"] / 1000
    require(abs(duration - meta["production_duration_ps"]) < 1e-8, "Step/duration mismatch")
    require(abs(times[-1] - times[0] - duration) < 1e-8, "Frame/duration mismatch")
    require(abs(times[0] - meta["first_frame_time_ps"]) < 1e-8 and
            abs(times[-1] - meta["last_frame_time_ps"]) < 1e-8, "Endpoint timestamp mismatch")
    protocol_ps = meta["short_equilibration_protocol_steps"] * meta["timestep_fs"] / 1000
    require(abs(times[0] - protocol_ps) < 1e-8, "First frame does not follow setup protocol")
    spacing = meta["sample_every_steps"] * meta["timestep_fs"] / 1000
    require(abs(spacing - meta["nominal_frame_spacing_ps"]) < 1e-8, "Sampling interval mismatch")
    require(np.all(np.abs(np.diff(times)[:-1] - spacing) < 1e-8) and
            0 < times[-1] - times[-2] <= spacing + 1e-8, "Unexpected frame spacing")

    expected_pdb_digest = meta["source_pdb_sha256"]
    require(re.fullmatch(r"[0-9a-f]{64}", expected_pdb_digest) is not None,
            "Invalid recorded PDB SHA256")
    source_check = {"status": "not_checked", "expected_sha256": expected_pdb_digest,
                    "note": "Supply --pdb to verify the original input bytes"}
    if args.pdb is not None:
        actual = file_digest(args.pdb)
        require(actual == expected_pdb_digest, "Source PDB SHA256 mismatch")
        source_check = {"status": "passed", "expected_sha256": expected_pdb_digest,
                        "actual_sha256": actual, "path": str(args.pdb)}

    generator_digest = file_digest(args.generator)
    require(generator_digest == meta["generator_sha256"], "Generator SHA256 mismatch")
    independent = np.asarray([horn_rmsd(c, coordinates[0]) for c in coordinates])
    direct = np.sqrt(np.mean(np.sum((coordinates - coordinates[0]) ** 2, axis=2), axis=1))
    independent_error = float(np.max(np.abs(independent - recorded)))
    direct_error = float(np.max(np.abs(direct - recorded)))
    require(independent_error < 2e-6, "Independent Horn RMSD disagrees with recorded RMSD")
    require(direct_error < 2e-6, "Aligned coordinates disagree with recorded RMSD")
    require(np.max(np.abs(coordinates.mean(axis=1))) < 2e-6, "Frames are not centered")
    require(recorded[0] < 2e-6, "Reference-frame RMSD is not zero")

    # Import definitions only; the generator's guarded main is never called.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("generate_demo_for_validation", args.generator)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    rng = np.random.default_rng(17)
    reference = rng.normal(size=(76, 3))
    reference -= reference.mean(axis=0)
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(rotation) < 0:
        rotation[:, 0] *= -1
    transformed = reference @ rotation + np.array([4.0, -3.0, 7.0])
    aligned, synthetic_rmsd = generator.align_ca(transformed, reference, np)
    require(synthetic_rmsd < 1e-12 and np.max(np.abs(aligned - reference)) < 1e-12,
            "Generator failed synthetic rigid-transform alignment")
    _, reflected_rmsd = generator.align_ca(reference * [-1, 1, 1], reference, np)
    require(reflected_rmsd > 0.1, "Generator incorrectly accepted a reflection")

    command = ["python", "scripts/generate_demo.py", "--pdb", "PATH_TO_1UBQ.pdb",
               "--output", "data/demo.json", "--seed", str(meta["seed"]),
               "--threads", str(meta["cpu_threads"]), "--minimize-iterations",
               str(meta["minimization_max_iterations"]), "--equilibration-steps",
               str(meta["short_equilibration_protocol_steps"]), "--production-steps",
               str(meta["production_steps_requested"]), "--sample-every-steps",
               str(meta["sample_every_steps"]), "--max-wall-seconds", str(meta["max_wall_seconds"])]
    data_digest = file_digest(args.data)
    return {
        "status": "passed", "validator_numpy_version": np.__version__,
        "checks": ["shape, finite values, unique residues", "units and actual timestamps",
                   "duration and sampling match completed steps and timestep",
                   "recorded generator SHA256", "independent Horn quaternion RMSD recomputation",
                   "direct RMSD of aligned coordinates", "centered frames",
                   "synthetic rigid rotation and translation removed",
                   "reflection not accepted as proper rotation"],
        "source_pdb_verification": source_check,
        "generator_verification": {"status": "passed", "sha256": generator_digest},
        "independent_rmsd_method": "Horn quaternion largest-eigenvalue method (not generator Kabsch SVD)",
        "maximum_rmsd_difference_angstrom": independent_error,
        "maximum_aligned_direct_rmsd_difference_angstrom": direct_error,
        "synthetic_rigid_transform_rmsd_angstrom": synthetic_rmsd,
        "frame_count": len(frames), "residue_count": len(residues),
        "first_time_ps": float(times[0]), "last_time_ps": float(times[-1]),
        "minimum_rmsd_angstrom": float(recorded.min()), "maximum_rmsd_angstrom": float(recorded.max()),
        "demo_json_bytes": args.data.stat().st_size, "demo_json_sha256": data_digest,
        "reproduction_command_template": shlex.join(command),
        "command_note": "Template reconstructed from recorded settings; substitute a local PDB matching source_pdb_sha256. No MD was run by this validator.",
        "recorded_historical_generation_command":
            BUNDLED_HISTORICAL_COMMAND if data_digest == BUNDLED_DEMO_SHA256 else None,
        "historical_command_note": "Original local invocation, available only for the bundled dataset identified by its SHA256.",
    }


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root / "data" / "demo.json")
    parser.add_argument("--pdb", type=Path)
    parser.add_argument("--generator", type=Path, default=root / "scripts" / "generate_demo.py")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args)
        output = args.output if args.output is not None else args.data.parent / "validation.json"
        require(output.resolve() not in (args.data.resolve(), args.generator.resolve()),
                "Validation output must not overwrite data or generator")
        if args.pdb is not None:
            require(output.resolve() != args.pdb.resolve(), "Validation output must not overwrite source PDB")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp.json")
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, output)
        print(json.dumps(report, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"VALIDATION FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
