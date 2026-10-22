# FEA to SolTrace

## What Does This Demonstrate?

This example connects finite-element analysis (FEA) of wind-deformed heliostats
to optical performance predictions. It:

1. Isolates reflective facets from reference and transient STL meshes.
2. Computes area-weighted surface normals, tracking errors, and slope-error statistics.
3. Compares SolTrace simulations of an ideal surface, a uniform slope-error model,
   and the explicitly triangulated deformed surface.
4. Provides interactive inspection of deformation statistics and optical results.
5. Uses random forests to fill missing operating points in an experimental grid.

The scripts consume existing FEA exports; they do not run a structural solver.
Synthetic predictions are model estimates, not additional FEA or ray-tracing runs.

## What Do I Need?

### Environment and Dependencies

- A 64-bit Python environment compatible with the native libraries. Python 3.11
  is a suggested starting point, not a certified or pinned project requirement.
- Windows is the primary setup described here. The SolTrace wrapper contains
  Linux/macOS library-loading branches, but those require separately built native
  libraries and are not a ready-to-run alternative to the supplied Windows DLLs.
- Python packages are listed in [requirements.txt](requirements.txt): NumPy,
  pandas, SciPy, trimesh, Matplotlib, and scikit-learn.
- Tkinter/Tcl-Tk and a graphical desktop for the post-processing application.
  Tkinter is normally included with the python.org Windows installer, rather
  than installed with pip.
- Optional notebook support: JupyterLab and ipykernel for
  [3_post_processing.ipynb](3_post_processing.ipynb).
- Sufficient memory and compute time for large meshes and ray datasets. No fixed
  memory or runtime minimum has been established. Start with reduced ray counts.

The requirements file is not a lockfile: package versions are unpinned.
Record the installed versions when reproducing results.

### Native SolTrace Libraries

Ray tracing uses the local [api/pysoltrace.py](api/pysoltrace.py) wrapper, not a
separate pip-installed SolTrace package. Its Windows loader expects these files
relative to the working directory:

```text
api/
    pysoltrace.py
    coretrace_api.dll
    embree4.dll
    tbb12.dll
    tbbmalloc.dll
```

Use matching builds of SolTrace, Embree, and their runtime dependencies, with the
same architecture as Python. If binaries are absent from a clean checkout,
obtain or build them from the associated SolTrace build before running ray tracing
in step 3.
Install any compiler runtime required by that build, such as the matching
Microsoft Visual C++ runtime. A DLL load failure can also mean a dependent DLL
is missing, even when the named DLL exists.

[api/copylot.py](api/copylot.py) and the SolarPILOT DLL are not used by the
numbered workflow.

### Input Data and Directory Layout

Supply the reference and transient STL exports under this layout:

```text
FEA_2_Trace/
    1_isolate_mesh_batch.py
    2_ray_tracing_images.py
    3_post_processing.py
    3_post_processing.ipynb
    4_create_synthetic_data.py
    5_compare_synthetic_versions.py
    requirements.txt
    api/
    results/
    stl_files/
        15 elevation 0 azimuth degree/
            structural steel 0s.stl
            4mps/
                structural steel 0.2s.stl
                structural steel 5s.stl
                isolated_meshes/          # generated
            8mps/
            12mps/
            16mps/
```

- Case names must start with the elevation and contain the azimuth as their
  third space-separated token, as in the example above. Angles are in degrees.
- Each case directory must contain exactly one reference `.stl`, excluding
  generated filenames containing `iso_mesh`.
- Immediate subdirectories of each case must be wind cases named like `4mps`.
- Transient STL filenames must end in a numeric time followed by `s.stl`.
  Scientific notation, such as `1e-6s.stl`, is supported.
- Reference and transient meshes must preserve face ordering and topology:
  reflective-face indices selected from the reference are reused on each slice.
- The undeformed reflective surface must be planar, with outward normals matching
  the expected orientation. The expected normal is
  `(-cos(elevation)*cos(azimuth), sin(elevation), -cos(elevation)*sin(azimuth))`.
- STL files do not encode units. Supply geometry consistent with the optical
  model's meter-based dimensions; the workflow does not automatically convert units.
- The default ray-tracing filter requires a slice whose parsed time is exactly
  `5.0` seconds. Without it, no new cases will be traced.

Directory names alone are not sufficient input: verify that the actual STL files
are present after checkout or archive extraction. The archive helper
[stl_files/unzip_files_UPDATE.bat](stl_files/unzip_files_UPDATE.bat) contains a
machine-specific source path and deletes archives after extraction. Do not run it
unchanged; extract manually or review and adapt it first.

Only load trusted pandas pickle files. They can execute code when read.

## How Do I Run It?

### 1. Set Up the Checkout

Clone the containing repository and change to this example's `FEA_2_Trace`
directory. Run all commands from that directory: most paths, including DLL and
mesh paths, are relative to the working directory.

In PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import numpy, pandas, scipy, trimesh, matplotlib, sklearn; import tkinter; print('Imports OK')"
```

These commands use the environment's Python directly, so PowerShell activation
is unnecessary. Select that interpreter in VS Code too. To verify Tkinter opens
a window, run:

```powershell
.\.venv\Scripts\python.exe -m tkinter
```

For notebooks, additionally install `jupyterlab ipykernel` into this environment
and select its kernel. The numbered scripts below are sufficient without Jupyter.

Populate the STL directories and native-library directory described above.
Existing CSV summaries alone do not replace the pickle inputs used by later
scripts. Pickles are ignored by this example's Git configuration, so expect to
regenerate them in a clean checkout.

### 2. Isolate Meshes and Calculate Errors

```powershell
.\.venv\Scripts\python.exe .\1_isolate_mesh_batch.py
```

The current default `plot_meshes = False` avoids opening mesh viewers during the
batch. Enable it in the script for visual inspection. The script exports
reflective meshes and saves both summaries after each processed slice.

On restart, it skips identities already loaded from the summary pickle:
elevation, azimuth, wind speed, and simulation time. If inputs or calculation
settings change, archive the existing summaries or choose new load/save
basenames before recomputing; existing rows are not automatically invalidated.

### 3. Run the Optical Comparison

Before a first test, review [2_ray_tracing_images.py](2_ray_tracing_images.py):

- `N_RAYS = 1.e7` requests 10 million ray hits per simulation. Temporarily use
  a smaller value, such as `1.e5`, for a smoke test. Lower counts increase noise
  and can affect numerical assertions.
- The `ST.run(...)` call uses `nthread = 20`; adjust it to your machine.
- Only simulation time `5.0` seconds is traced by default.
- The receiver distance is 500 m, the flux grid is 100 by 100, and DNI is
  1000 W/m^2. Each eligible row runs three optical scenarios.
- Explicit mesh import is capped at 100,000 faces. Larger meshes are truncated;
  review this limit before treating results as a full-mesh calculation.

```powershell
.\.venv\Scripts\python.exe .\2_ray_tracing_images.py
```

Completed trace rows are checkpointed and reused on restart. To rerun with changed
ray counts or optical settings, archive the trace-results pickle or choose a new
output basename; saved traces are not automatically invalidated by setting changes.

### 4. Inspect and Aggregate Results

```powershell
.\.venv\Scripts\python.exe .\3_post_processing.py
```

This writes grouped averages, then opens a Tkinter application for selecting
operating conditions and timesteps, inspecting slope errors, and comparing
encircled-energy curves and receiver flux. Figure saving is opt-in through
the application controls. Close the window to finish the script.

For a metrics-only workflow without native SolTrace libraries, skip step 3 and
change `RESULTS_PATH` in [3_post_processing.py](3_post_processing.py) to
`"results/processed_meshes.pkl"` before running it. Grouped averages and mesh
inspection remain available; optical panels report that trace results are missing.

### 5. Generate Synthetic Operating Points

```powershell
.\.venv\Scripts\python.exe .\4_create_synthetic_data.py
```

The current input is `results/grouped_avg_results_v4.csv`, produced by the previous
step, and the output is `results/synthetic_heliostat_data_v4.csv`. Both paths are
configured near the top of [4_create_synthetic_data.py](4_create_synthetic_data.py).

The training table needs the three operating-point columns and all twelve metric
columns listed in `output_cols` in that script. Supply nonempty, finite numeric
training data with one row per operating point. The script trains one
100-tree random forest per metric with `random_state=42` and uses all available
cores. It retains observed rows and predicts only missing grid points.

### 6. Optionally Compare Synthetic Versions

[5_compare_synthetic_versions.py](5_compare_synthetic_versions.py) requires all
four versions (`v1`, `v2`, `v3`, `v4`); step 5 generates only `v4` with the current
configuration. Obtain the other datasets from previous runs, or generate them
from their corresponding grouped inputs with appropriately changed paths.

The comparison script currently searches beside itself, whereas the generator
writes into `results/`. Before running it, change its `DATA_DIR` assignment to:

```python
DATA_DIR = Path(__file__).resolve().parent / "results"
```

Then run:

```powershell
.\.venv\Scripts\python.exe .\5_compare_synthetic_versions.py
```

Each CSV must have unique elevation/azimuth/wind keys, the same operating-point
grid, and the three comparison metrics: elevation tracking error, azimuth tracking
error, and weighted mean slope error. The script validates these conditions.

## What Should I Expect?

| Stage | Outputs and confirmation |
| --- | --- |
| Mesh processing | A reference `iso_mesh_*.stl` in each case directory; transient `iso_mesh_*.stl` files in each wind case's `isolated_meshes/`; `results/processed_meshes.pkl` and `.csv`. One summary row represents one processed elevation/azimuth/wind/time identity. |
| Ray tracing | `results/processed_meshes_wTrace.pkl`, with `ST_results` dictionaries for traced rows. Each dictionary includes `ST_baseline`, `ST_mean_slope_error`, and `ST_mesh`, containing optical statistics, flux maps, and encircled-energy results. Nonselected times remain untraced. |
| Post-processing | `results/grouped_avg_results_v4.pkl` and `.csv`, averaging numeric metrics over time for each elevation/azimuth/wind group; an interactive window; optional PNGs under `results/figures/`. |
| Synthetic generation | `results/synthetic_heliostat_data_v4.csv`. The target grid has 7 elevations (0 to 90 degrees), 13 azimuths (0 to 180 degrees), and 4 wind speeds (4 to 16 m/s): 364 operating points. Exactly 364 rows are expected when the original inputs have unique keys entirely within this grid. Original rows outside the grid are retained. |
| Version comparison | A printed pairwise-error summary and a displayed comparison plot. With the `DATA_DIR` adjustment above, the PNG is `results/synthetic_data_version_error_comparison.png`. |

Tracking and slope errors use milliradians; orientation angles use degrees.
Average-normal components are dimensionless. Ray tracing is statistical, so
bit-for-bit optical agreement across environments is not an acceptance criterion.
The trace script checks near-100% interception and consistency of cumulative
power across its three scenarios; assertion failures require investigation.

After synthetic generation, a quick data check is:

```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; d=pd.read_csv('results/synthetic_heliostat_data_v4.csv'); k=['expected_elevation_angle_deg','expected_azimuth_angle_deg','wind_speed_mps']; print('Rows:',len(d)); print('Duplicate keys:',d.duplicated(k).sum()); print('Missing cells:',d.isna().sum().sum())"
```

For unique, in-grid training data, expect 364 rows, zero duplicate keys, and no
missing values in the operating-point and twelve predicted metric columns.
Other columns carried from the original table may be empty on predicted rows.
Successful generation does not establish predictive accuracy or physical
consistency: the twelve independent regressors do not enforce unit normals or
relationships between angles and errors, and predictions outside the sampled
FEA conditions need separate validation.

If a run produces no new work, check saved identities and the 5-second trace
filter before assuming a failure. If meshes cannot be loaded later, check the
working directory and the stored mesh paths. Keep generated meshes alongside
their summaries. To reproduce a result, record the package versions, native
library build, input dataset, and any edited script constants.