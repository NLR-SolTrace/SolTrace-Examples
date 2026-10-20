# National Solar Thermal Test Facility

This example shows building a heliostat field using the `pysoltrace` Python bindings to SolTrace&trade;. The heliostat field is modeled off of the National Solar Thermal Test Facility (NSTTF). This example goes through setting up the data used for a simulation, running a simulation, and generating a flux map of intersection locations on the target.

NOTE: You may see `chedder` warnings for `__declspec(dllexport)`, `__declspec(dllimport)`, `RunnerStatistics`, `p_callback`, and `fs::path`. These warnings apply to types that aren't used by the python bindings, and are harmless. There are plans to handle these better.

## SolTrace Compatibility

This example was developed and tested with:

- SolTrace: 4.0.0-beta_v2
- pysoltrace: 0.1.0
- Python: 3.14
- Operating System: Windows

To ensure reproducibility, use the versions listed above. The example has not been validated against other versions.

---

# What does this demonstrate?

This example demonstrates using the `pysoltrace` bindings as a script. The `pysoltrace` bindings are functions that modify the state of the DLL, and have little state themselves (just a reference to the DLL). For an exmaple that uses python objects, see NSTTF example with `PySolTrace` (in development).

At the begining of `nsttf.py`, some constants are defined, and the file system is set up to access the required data. Functions are defined for adding the various optical properties, the tower, the G3P3 receiver components (currently not usable), the Solar 1 receiver, and the heliostat field. The data for the heliostats are loaded in on `import` and are referenced by `add_heliostats`. The `ArbitraryHeliostat` class is used because the spacing of NSTTF heliostats is nor regular as expected by `Heliostat`. Next, the `make_NSTTF` function is defined which organizes the plant's geometry creation into a single location. For arguments, it takes the api, the solar position to simulate, and a boolean to toggle which target is used. Then, the plotting function, `plot_heat_map`, is defined.

The model is run in the `__name__` gaurd (`if __name__ == '__main__'`). The `pysoltrace` `api` is initialized as `stapi`. This creates the reference to the SolTrace DLL, acts as the access point for all calls to change the SolTrace simulation, and will free the context once the object is destroyed. The simulation parameters are set with `stapi.data.parameters.set`. The sun's position is calculated as a vector with `stapi.data.sun.vector`. That vector is then used to add the sun to the simulation with `stapi.data.sun.add`. This example uses the Buie CSR sun model. Then, the NSTTF plant geometry is created with `make_NSTTF`. The simulation data is saved to JSON for demonstration. The JSON file is not used in this example, but they can be loaded using `api.data.json.load`. The simulation is then set up using the Optix runner, however this should be changed to the Embree or Native runners if you don't have a GPU. The simulation is then run and reported. The results of the simulation are used to create a `pandas` `DataFrame`. Note that the number of intersections must be passed to functions that get results, because the arrays need to be allocated in python. The number of intersections can be determined by `len(stapi.result)` or `stapi.result.num`. Finally, the results are used to generate a flux map of the target. The target hits are extracted from the `DataFrame`. Plotting parameters are set. The figure is created, passed to `plot_heat_map`, and shown.

## Learning Objectives

After completing this example, users should be able to:

- Add optical properties
- Add elements
- Set simulation parameters
- Determine solar position
- Add a sun model
- Set up / run / report a simulation
- Use the simulation results to make a heat map

---

# What do I need?

## Software Requirements

- SolTrace >= 4.0.0-beta_v2
- PySolTrace >= 0.1.0
- Python >= 3.8

## Input Files

Required files:

```text
NSTTF/
├── nsttf_data/
    ├── canting/
    ├── coordinates.csv
    ├── ids.csv
├── nsttf.py
├── reference_nsttf.json
└── reference_plot.png
```

- `canting/` - Directory containing CSVs describing NSTTF heliostat geometry and canting as designed.
- `coordinates.csv` - CSV containing the locations of each heliostat.
- `ids.csv` - CSV containing the names of each heliostat.

## Environment Setup

### Create a Virtual Environment

To isolate this example from others, navigate to `NSTTF/` to set up virtual environment. 

```bash
python -m venv .venv
```

Activate:

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### Install Dependencies


```bash
pip install "pysoltrace>=0.1.0"
```

NOTE: right now not on PyPi, ask Nick for .whl, only built for Windows right now. Install a wheel with:
```bash
pip install path/to/pysoltrace.whl
```

## Data Acquisition

No external data is required.

---

# How do I run it?

Starting from a clean checkout:

## Step 1: Clone Repository

```bash
git clone https://github.com/NLR-SolTrace/SolTrace-Examples.git
cd ./SolTrace-Examples/NSTTF
```

## Step 2: Create Environment

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install "pysoltrace>=0.1.0"
```

NOTE: right now not on PyPi, ask Nick for .whl, only built for Windows right now. Install a wheel with:
```bash
pip install path/to/pysoltrace.whl
```

## Step 4: Verify SolTrace Installation

```bash
python -c "import pysoltrace; print(pysoltrace.__version__)"
```

Expected result:

```text
0.1.0
```

## Step 5: Run Example

```bash
python ./nsttf.py
```

## Optional Configuration

Several things can be changed about this simulation:

```python
"""
Users can modify default parameters using the simulation_parameters object, example parameters and their defaults:
    number_of_rays:           int  =   1,000,000
    max_number_of_rays:       int  = 100,000,000
    include_sun_shape_errors: bool = True
    include_optical_errors:   bool = True
"""
sim_params = _STC.simulation_parameters(...)

...

"""
Users can change the solar position calculator, the time that is simulated, or the sun model using the dot_h.SolarPositionCalculationMethod IntEnum, the sun_datetime object, and the sun object, repsectively.
"""
# (year, month, day, hour, minute, second)
dt = _STC.sun_datetime(2025, 6, 20, 12)
# available methods: LEGACY, DUFFIE, SOLPOS, SPA_ORIGINAL, SPA
calc = dot_h.SolarPositionCalculationMethod.SPA
buie = _STC.sun(0, *sun_pos, .05, _STC.sun_shape.BUIE_CSR.value)

...

"""
Users can modify which runner is used with the dot_h.st_runner_type_t IntEnum, available runners are: EMBREE, OPTIX, NATIVE.
NOTE: The Optix runner requires an Nvidia GPU.
NOTE: The Native runner should be run with much fewer rays (e.g., ~10,000)
"""
runner_type = dot_h.st_runner_type_t.OPTIX
```

---

# What should I expect?

## Reference Output

Example output:

```text
Initialized api
Set simulation parameters: 
simulation_parameters(parameter values...)
Added sun: sun(sun values...)
Added NSTTF geometry
Dumped data into SolTrace JSON: path\to\SolTrace-Examples\NSTTF\nsttf.json
Running Optix simulation...
Simulated (some number...) intersections.
```

A plot should appear after a few seconds. Depending on the time of day simulated the heat map will skew. For example, June 20th, 2025, was simulated:

At noon:
![Reference Heat Map at Noon](https://github.com/NLR-SolTrace/SolTrace-Examples/blob/main/NSTTF/reference_plot_12.png)

At 9am:
![Reference Heat Map at 9am](https://github.com/NLR-SolTrace/SolTrace-Examples/blob/main/NSTTF/reference_plot_09.png)

At 3pm:
![Reference Heat Map at 3pm](https://github.com/NLR-SolTrace/SolTrace-Examples/blob/main/NSTTF/reference_plot_15.png)

After the plot is closed, you should see.

```text
Freed context (0x some address...) with code (0) from SolTrace DLL ...
```

## Generated Files

The example should generate:

```text
NSTTF/
...
└── nsttf.json
```

- `nsttf.json` - SolTrace JSON of simulation data created in the script.

## Expected Results

- Flux map generated successfully
- Runtime of approximately 10 seconds on a typical laptop (with RTX GPU)

## Validation

Users can confirm success by checking:

- [ ] Input JSON is similar to the reference JSON
- [ ] Generated plots appear similar to the reference images

---

# Acknowledgements

This example would not be possible without the help of Rebecca Mitchell, Luke McLaughlin and the NSTTF and G3P3 teams at Sandia National Laboratory. The data for this example comes from Aaron Spieles and the OpenCSP team.

OpenCSP Team. OpenCSP: An Environment for Collaborative CSP Optical Technology Development. https://opencsp.sandia.gov.

---

# License

See [SolTrace licence](https://github.com/NLR-SolTrace/SolTrace-Examples/blob/main/LICENSE.md).