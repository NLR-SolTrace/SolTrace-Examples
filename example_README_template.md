# Example Name

Short one-paragraph description of the example and its purpose.

## SolTrace Compatibility

This example was developed and tested with:

- SolTrace: X.Y.Z
- PySolTrace: X.Y.Z
- Python: X.Y
- Operating System(s): Windows/Linux/macOS

To ensure reproducibility, use the versions listed above. The example has not been validated against other versions.

---

# What does this demonstrate?

Describe the specific capability, workflow, or concept demonstrated by this example.

For example:

- Creating a solar field model
- Defining optical properties
- Running a ray-tracing simulation
- Post-processing simulation results
- Integrating SolTrace with another tool

## Learning Objectives

After completing this example, users should be able to:

- Objective 1
- Objective 2
- Objective 3

---

# What do I need?

## Software Requirements

- SolTrace X.Y.Z
- PySolTrace X.Y.Z
- Python X.Y
- Additional dependencies

## Python Dependencies

```bash
pip install -r requirements.txt
```

or

```bash
pip install pysoltrace matplotlib numpy
```

## Input Files

Required files:

```text
example/
├── input_1.ext
├── input_2.ext
└── example.py
```

Describe each input file:

- `input_1.ext` - Purpose
- `input_2.ext` - Purpose

## Environment Setup

### Create a Virtual Environment

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
pip install -r requirements.txt
```

## Data Acquisition

If external data is required:

1. Obtain data from ...
2. Place files in ...
3. Verify directory structure matches ...

---

# How do I run it?

Starting from a clean checkout:

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd <repository-name>
```

## Step 2: Create Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Verify SolTrace Installation

```bash
python -c "import pysoltrace"
```

Expected result:

```text
No errors
```

## Step 5: Run Example

```bash
python example.py
```

or

```bash
python examples/example.py
```

## Optional Configuration

Document any configurable parameters:

```python
num_rays = 10000
sun_shape = "pillbox"
```

Explain effects of changing these parameters.

---

# What should I expect?

## Console Output

Example:

```text
Simulation started...
100000 rays traced
Simulation completed successfully
```

## Generated Files

The example should generate:

```text
results/
├── report.csv
├── efficiency.csv
└── plot.png
```

## Expected Results

Describe expected numerical results, trends, or behavior.

For example:

- Optical efficiency approximately 72%
- Flux map generated successfully
- Runtime of approximately 10 seconds on a typical workstation

## Validation

Users can confirm success by checking:

- [ ] Simulation completes without errors
- [ ] Output files are generated
- [ ] Results fall within expected ranges
- [ ] Generated plots appear similar to the reference images

## Reference Output

Include a screenshot, plot, or sample output if appropriate.

```text
Reference efficiency: 72.3%
Reference intercepted power: 985 W
```

---

# Troubleshooting

## Common Issues

### SolTrace Not Found

Error:

```text
Unable to load SolTrace library
```

Resolution:

- Verify installation path
- Verify pinned version
- Confirm architecture compatibility

### Missing Input Files

Error:

```text
File not found
```

Resolution:

- Verify required files are present
- Verify working directory

---

# Reproducibility Notes

To reproduce the published results:

- Use the pinned software versions listed above.
- Use the provided input files unchanged.
- Run the example using the documented commands.
- Record any deviations from the documented environment.

---

# References

- SolTrace User Documentation
- PySolTrace Documentation
- Relevant publications or technical reports

---

# License

Specify the applicable license for the example and any included data files.