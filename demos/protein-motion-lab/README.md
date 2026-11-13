# Protein Motion Lab

An interactive viewer for a real, short molecular-dynamics trajectory of
ubiquitin. Rotate the protein, scrub through sampled frames, and compare the
backbone with its aligned starting structure while inspecting measured motion.

The bundled example is a local CPU software demonstration. It is not a Cheaha
GPU benchmark, an equilibrium measurement, a myosin simulation, or a drug result.
It provides a small working foundation for sharing and inspecting later research.

## Run the viewer

No JavaScript packages, external services, model keys or build tools are needed:

```bash
python -m http.server 8000 --directory demos/protein-motion-lab
```

Then open `http://localhost:8000`. If this folder was downloaded on its own, run
`python -m http.server 8000` from inside the folder instead.

The browser reads the checked-in `data/demo.json`. Playback changes how quickly
frames are displayed; it does not change physical simulation time. Coordinates
are shown at their recorded scale. Only protein C-alpha atoms are displayed;
water and ions remain part of the simulated system but are hidden in the viewer.

## What the motion plot measures

Each displayed frame is centered and optimally rotated onto the first sampled
production frame using a Kabsch alignment of the C-alpha atoms. The RMSD plot
reports the root-mean-square C-alpha displacement after that alignment, in
angstroms. Thus whole-protein translation and rotation do not dominate the plot.
The first displayed frame has RMSD zero by definition.

The frame timestamps and simulation settings are preserved in the data's
metadata. A short trajectory demonstrates that the pipeline executes and that
the viewer can inspect the output. Its apparent stability does not establish
equilibration, conformational populations, clinical significance or convergence.

## Reproduce the example

Use a separate Python environment with the recorded OpenMM version:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
curl --fail --location https://files.rcsb.org/download/1UBQ.pdb --output 1UBQ.pdb
python scripts/generate_demo.py --pdb 1UBQ.pdb --seed 1001 --threads 2 \
  --minimize-iterations 200 --equilibration-steps 200 \
  --production-steps 1000 --sample-every-steps 20 --max-wall-seconds 120
python scripts/validate_demo.py --pdb 1UBQ.pdb
```

The generator records the source structure, seed, force field, solvent and
protocol, engine version, atom count, timestamps and coordinate transformation.
Its full command is in `data/validation.json` after generation. The bundled data
were generated with two CPU threads. No cluster job is required to view them.

Small numerical differences across platforms and libraries are expected; exact
trajectory bytes should not be treated as a portable physical reproducibility
criterion. Validate finite coordinates, geometry, units and analysis first.

## Offline single-file export

```bash
python scripts/build_standalone.py --output protein-motion-lab.html
```

Open the resulting file directly in a browser. The export includes the viewer
and its small dataset and makes no external network requests.

## Data and provenance

- Initial protein: [RCSB PDB 1UBQ](https://www.rcsb.org/structure/1UBQ).
- Initial coordinate file: <https://files.rcsb.org/download/1UBQ.pdb>.
- MD engine: [OpenMM](https://openmm.org/).
- Generator and analysis: `scripts/generate_demo.py`.
- Viewer input: `data/demo.json`.
- Run and analysis verification: `data/validation.json`.

The initial structure is an existing published protein structure. The generated
trajectory and analysis are a software demonstration derived from it; they are
not presented as a new biological discovery. The included code is MIT licensed;
the upstream structure and OpenMM retain their own attribution and terms.

## Validation

Data generation and analysis checks are documented with the generated data.
Browser checks cover playback, frame selection, structure rotation, CSV export,
offline export and narrow-screen layout. GPU performance, long trajectories and
scientific conclusions require separate validation.

The optional browser smoke script is `docs/browser-smoke.py`. It uses Playwright
and an installed Chromium (or Playwright's browser); set `CHROMIUM_PATH` if needed.
Serve this directory on port 8765, then run the script. To use a different server,
set `PROTEIN_MOTION_BASE_URL`. Its screenshots and downloaded CSV go to
`test-output/`, or the directory set in `PROTEIN_MOTION_TEST_OUTPUT`.
