#!/usr/bin/env python3
"""Generate a tiny real 1UBQ trajectory for Protein Motion Lab.

Local CPU only, two threads maximum, no downloads, no cluster jobs. This is a
software demonstration: a few picoseconds do not establish equilibration,
convergence, function, stability, drug response, or a new biological finding.
Only aligned protein C-alpha coordinates are saved, not the solvent trajectory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def align_ca(positions, reference, np):
    """Optimal proper rotation of centered row-vector coordinates, in angstrom."""
    centered = positions - positions.mean(axis=0)
    left, _, right_t = np.linalg.svd(centered.T @ reference)
    if np.linalg.det(left @ right_t) < 0:
        left[:, -1] *= -1
    aligned = centered @ (left @ right_t)
    rmsd = np.sqrt(np.mean(np.sum((aligned - reference) ** 2, axis=1)))
    return aligned, float(rmsd)


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdb", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data" / "demo.json")
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--threads", type=int, choices=(1, 2), default=2)
    parser.add_argument("--minimize-iterations", type=int, default=200)
    parser.add_argument("--equilibration-steps", type=int, default=200)
    parser.add_argument("--production-steps", type=int, default=1000)
    parser.add_argument("--sample-every-steps", type=int, default=20)
    parser.add_argument("--max-wall-seconds", type=float, default=120.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for name, lo, hi in (("seed", 1, 2147483646),
                         ("minimize_iterations", 1, 1000),
                         ("equilibration_steps", 0, 1000),
                         ("production_steps", 1, 2000),
                         ("sample_every_steps", 1, 100),
                         ("max_wall_seconds", 10, 120)):
        value = getattr(args, name)
        if not math.isfinite(value) or not lo <= value <= hi:
            parser.error(f"{name} must be in [{lo}, {hi}]")
    if os.environ.get("SLURM_JOB_ID"):
        parser.error("This demo generator runs locally only; no Slurm execution")
    if args.output.exists() and not args.overwrite:
        parser.error("Output already exists; use --overwrite explicitly")
    if not args.pdb.is_file() or args.pdb.stat().st_size > 2 * 1024 * 1024:
        parser.error("Supply the local 1UBQ PDB, no larger than 2 MiB")
    for key in ("OPENMM_CPU_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = str(args.threads)

    import numpy as np
    import openmm as mm
    from openmm import app, unit

    random.seed(args.seed)
    np.random.seed(args.seed)
    pdb_bytes = args.pdb.read_bytes()
    pdb = app.PDBFile(str(args.pdb))
    original_protein = [r for r in pdb.topology.residues()
                        if r.name not in ("HOH", "WAT")]
    if len(original_protein) != 76 or len({r.chain.index for r in original_protein}) != 1:
        raise ValueError("Expected one 76-residue ubiquitin chain")
    platform = mm.Platform.getPlatformByName("CPU")
    forcefield_files = ["amber14-all.xml", "amber14/tip3pfb.xml"]
    forcefield = app.ForceField(*forcefield_files)
    modeller = app.Modeller(pdb.topology, pdb.positions)
    modeller.deleteWater()
    modeller.addHydrogens(forcefield, pH=7.0, platform=platform)
    modeller.addSolvent(forcefield, model="tip3p", padding=1.0 * unit.nanometer,
                        ionicStrength=0.15 * unit.molar, neutralize=True)
    system = forcefield.createSystem(
        modeller.topology, nonbondedMethod=app.PME,
        nonbondedCutoff=1.0 * unit.nanometer,
        constraints=app.HBonds, rigidWater=True, ewaldErrorTolerance=0.0005)
    integrator = mm.LangevinMiddleIntegrator(
        300 * unit.kelvin, 1 / unit.picosecond, 2 * unit.femtosecond)
    integrator.setRandomNumberSeed(args.seed)
    simulation = app.Simulation(modeller.topology, system, integrator, platform,
                                {"Threads": str(args.threads)})
    simulation.context.setPositions(modeller.positions)
    ca_atoms = [a for a in modeller.topology.atoms() if a.name == "CA"]
    if len(ca_atoms) != 76:
        raise ValueError("Expected precisely 76 protein C-alpha atoms")
    ca_indices = np.asarray([atom.index for atom in ca_atoms], dtype=int)
    residues = [{"id": f"{a.residue.chain.id}:{a.residue.id}",
                 "name": a.residue.name} for a in ca_atoms]
    if len({r["id"] for r in residues}) != len(residues):
        raise ValueError("Residue identifiers must be unique")

    setup_seconds = time.perf_counter() - started
    phase_started = time.perf_counter()
    simulation.minimizeEnergy(tolerance=10 * unit.kilojoule_per_mole / unit.nanometer,
                              maxIterations=args.minimize_iterations)
    minimization_seconds = time.perf_counter() - phase_started
    simulation.context.setVelocitiesToTemperature(300 * unit.kelvin, args.seed + 1)
    while simulation.currentStep < args.equilibration_steps:
        if time.perf_counter() - started >= args.max_wall_seconds:
            raise RuntimeError("Wall budget reached before completing the short setup protocol")
        simulation.step(min(20, args.equilibration_steps - simulation.currentStep))

    frames = []
    reference = None

    def record_frame():
        nonlocal reference
        state = simulation.context.getState(getPositions=True, getEnergy=True)
        positions = np.asarray(state.getPositions(asNumpy=True).value_in_unit(unit.angstrom))
        ca = positions[ca_indices]
        if reference is None:
            reference = ca - ca.mean(axis=0)
        aligned, rmsd = align_ca(ca, reference, np)
        potential = state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        if not (np.isfinite(aligned).all() and math.isfinite(rmsd) and math.isfinite(potential)):
            raise RuntimeError("Non-finite coordinates, RMSD, or energy; no demo exported")
        frames.append({
            "time_ps": round(state.getTime().value_in_unit(unit.picosecond), 9),
            "positions_angstrom": np.round(aligned, 6).tolist(),
            "rmsd_angstrom": round(rmsd, 8),
            "potential_kj_mol": round(float(potential), 6),
        })

    record_frame()
    production_start_step = simulation.currentStep
    target = production_start_step + args.production_steps
    md_integrator_seconds = 0.0
    while simulation.currentStep < target:
        if time.perf_counter() - started >= args.max_wall_seconds:
            break
        chunk = min(args.sample_every_steps, target - simulation.currentStep)
        tick = time.perf_counter()
        simulation.step(chunk)
        md_integrator_seconds += time.perf_counter() - tick
        record_frame()
    completed_steps = simulation.currentStep - production_start_step
    if completed_steps == 0:
        raise RuntimeError("No production frames before wall budget; no demo exported")
    metadata = {
        "schema_version": 1, "protein": "Ubiquitin", "pdb_id": "1UBQ",
        "source_structure_url": "https://www.rcsb.org/structure/1UBQ",
        "source_pdb_url": "https://files.rcsb.org/download/1UBQ.pdb",
        "source_pdb_sha256": digest(pdb_bytes),
        "source_pdb_file": args.pdb.name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "OpenMM", "engine_version": mm.__version__,
        "python_version": sys.version.split()[0], "numpy_version": np.__version__,
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "system_xml_sha256": digest(mm.XmlSerializer.serialize(system).encode()),
        "platform": simulation.context.getPlatform().getName(),
        "cpu_threads": args.threads, "seed": args.seed,
        "forcefield_files": forcefield_files,
        "water_model": "TIP3P-FB", "water_geometry": "TIP3P",
        "ensemble": "NVT; fixed periodic box, no barostat",
        "temperature_k": 300.0, "friction_per_ps": 1.0, "timestep_fs": 2.0,
        "nonbonded_method": "PME", "cutoff_nm": 1.0,
        "ewald_error_tolerance": 0.0005, "constraints": "HBonds; rigid water",
        "padding_nm": 1.0, "ionic_strength_molar": 0.15,
        "preprocessing": "Removed crystal waters; added hydrogens at pH 7; solvated and neutralized with NaCl",
        "minimization_max_iterations": args.minimize_iterations,
        "minimization_tolerance_kj_mol_nm": 10.0,
        "short_equilibration_protocol_steps": args.equilibration_steps,
        "short_equilibration_protocol_duration_ps": args.equilibration_steps * 0.002,
        "scientific_equilibration_established": False,
        "production_steps_requested": args.production_steps,
        "production_steps_completed": completed_steps,
        "production_duration_ps": completed_steps * 0.002,
        "sample_every_steps": args.sample_every_steps,
        "nominal_frame_spacing_ps": args.sample_every_steps * 0.002,
        "first_frame_time_ps": frames[0]["time_ps"],
        "last_frame_time_ps": frames[-1]["time_ps"],
        "frame_count": len(frames), "ca_atom_count": len(ca_atoms),
        "total_solvated_atom_count": system.getNumParticles(),
        "position_units": "angstrom", "rmsd_units": "angstrom",
        "time_units": "picosecond", "potential_energy_units": "kJ/mol",
        "alignment": "Each C-alpha frame is centered and Kabsch-aligned to the first sampled production frame",
        "rmsd_reference": "First sampled production frame; same 76 C-alpha atoms",
        "sampling_note": "An initial frame and each sampled chunk; timestamps preserve any final partial interval",
        "termination": "completed" if simulation.currentStep == target else "wall_budget",
        "max_wall_seconds": args.max_wall_seconds,
        "wall_seconds": round(time.perf_counter() - started, 6),
        "setup_seconds": round(setup_seconds, 6),
        "minimization_seconds": round(minimization_seconds, 6),
        "production_integrator_seconds": round(md_integrator_seconds, 6),
        "purpose": "Real, short local MD for an educational software demo",
        "limitations": [
            "Picosecond-scale software demonstration; not a new biological discovery.",
            "The short setup protocol does not establish equilibration or convergence.",
            "No inference about protein function, stability, disease, or drug efficacy.",
            "Only C-alpha coordinates are exported; solvent and other atoms remain in the simulated system.",
            "Alignment removes rigid translation and rotation; the display shows internal motion.",
            "A random seed records initialization; exact trajectories can differ across hardware or software builds.",
        ],
    }
    payload = {"metadata": metadata, "residues": residues, "frames": frames}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp.json")
    temporary.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n")
    os.replace(temporary, args.output)
    print(json.dumps({"output": str(args.output), "frames": len(frames),
                      "ca_atoms": len(ca_atoms), "production_ps": completed_steps * 0.002,
                      "wall_seconds": metadata["wall_seconds"],
                      "termination": metadata["termination"]}, sort_keys=True))


if __name__ == "__main__":
    main()
