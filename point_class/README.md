# Point Class

This example demonstrates many of the capabilities of the Point class. If there is functionality defined in the source that is missed, please open an issue referencing this example and the functionality that is missed.

NOTE: You may see `chedder` warnings for `__declspec(dllexport)`, `__declspec(dllimport)`, `RunnerStatistics`, `p_callback`, and `fs::path`. These warnings apply to types that aren't used by the python bindings, and are harmless. There are plans to handle these better.

## SolTrace Compatibility

This example was developed and tested with:

- SolTrace: n/a
- pysoltrace: 0.1.0
- Python: 3.14
- Operating System: Windows

To ensure reproducibility, use the versions listed above. The example has not been validated against other versions.

---

# What does this demonstrate?

This example demonstrates the following capabilities of the Point class:
- "casting" to str, formatted str, boolean, float, int, iterable
- using indicies to get members (i.e., using `[]`)
- number of elements: `len()`
- negation: `-`
- magnitude: `abs()`
- addition: `+` and `+=`
- subtraction: `-` and `-=`
- multiplication: `*` and `*=`
- integer division: `//` and `//=`
- division: `/` and `/=`
- cross product with Point/list/np.array: `@` and `@=`
- matrix multiplication when Point on right hand side of operator: `@`
- boolean operations: `==`, `!=`, `<`, `>`, `<=`, `>=`
- reduction: `point.reduce()`
- magnitude: `point.radius()`
- direction: `point.unitize()`
- as a list: `point.as_list()`
- as a np.array: `point.as_array()`
- from a list/np.array: `Point.from_list(l)`

## Learning Objectives

After completing this example, users should be able to:

- Know capabilities of the Point class
- Know when and which math operation maps to the python operation 

---

# What do I need?

## Software Requirements

- PySolTrace >= 0.1.0
- Python >= 3.8

## Input Files

Only example file required:

```text
point_class/
└── example.py
```

## Environment Setup

### Create a Virtual Environment

To isolate this example from others, navigate to `point_class/` to set up virtual environment. 

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
cd ./SolTrace-Examples/point_class
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
python ./example.py
```

---

# What should I expect?

## Reference Output

Example output:

```text
Examples of printing:
a -> [6.00, 0.00, 8.00]
a -> [6.0000e+00, 0.0000e+00, 8.0000e+00]

Examples of boolean casting:
bool(a) -> True
bool(zeros) -> False

Example of float casting:
float(a) -> 10.0

Example of int casting:
int(a) -> 10

Example of iterating:
for v in a: sum += v -> 14

Examples of list-ish interface:
a[1] -> 0
a[1] = -17 -> -17

Example of length:
len(a) -> 3

Example of negation:
-a -> [-6.00, 17.00, -8.00]

Example of absolute value:
abs(a) -> 19.72308292331602

Examples of adding:
a + b         -> [9.00, -17.00, 11.00]
a + 1         -> [7.00, -16.00, 9.00]
a + 2.1       -> [8.10, -14.90, 10.10]
a + [3, 0, 3] -> [9.00, -17.00, 11.00]

Examples of right adding:
1 + b         -> [4.00, 1.00, 4.00]
2.1 + b       -> [5.10, 2.10, 5.10]
[6, 0, 8] + b -> [9.00, 0.00, 11.00]

Examples of inplace adding:
c += a + b     -> [9.00, -17.00, 11.00]
c += 1         -> [10.00, -16.00, 12.00]
c += 2.1       -> [12.10, -13.90, 14.10]
c += [6, 0, 8] -> [18.10, -13.90, 22.10]

Examples of subtracting:
a - b         -> [3.00, -17.00, 5.00]
a - 1         -> [5.00, -18.00, 7.00]
a - 2.1       -> [3.90, -19.10, 5.90]
a - [3, 0, 3] -> [3.00, -17.00, 5.00]

Examples of right subtracting:
1 - b         -> [-2.00, 1.00, -2.00]
2.1 - b       -> [-0.90, 2.10, -0.90]
[6, 0, 8] - b -> [3.00, 0.00, 5.00]

Examples of inplace subtracting:
c -= a + b     -> [9.10, 3.10, 11.10]
c -= 1         -> [8.10, 2.10, 10.10]
c -= 2.1       -> [6.00, -0.00, 8.00]
c -= [6, 0, 8] -> [0.00, -0.00, 0.00]

Examples of multiplying:
a * b         -> [18.00, 0.00, 24.00]
a * 4         -> [24.00, -68.00, 32.00]
a * 2.1       -> [12.60, -35.70, 16.80]
a * [3, 0, 3] -> [18.00, 0.00, 24.00]

Examples of right multiplying:
4 * b         -> [12.00, 0.00, 12.00]
2.1 * b       -> [6.30, 0.00, 6.30]
[6, 0, 8] * b -> [18.00, 0.00, 24.00]

Examples of inplace multiplying:
c *= b         -> [18.00, -0.00, 24.00]
c *= 4         -> [24.00, -68.00, 32.00]
c *= 2.1       -> [50.40, -142.80, 67.20]
c *= [6, 0, 8] -> [302.40, -0.00, 537.60]

Examples of floordiv:
a // d         -> [1.00, -4.00, 3.00]
a // 4         -> [1.00, -5.00, 2.00]
a // 2.1       -> [2.00, -9.00, 3.00]
a // [3, 10, 3] -> [2.00, -2.00, 2.00]

Examples of inplace floordiv:
c //= d         -> [1.00, -4.00, 3.00]
c //= 4         -> [1.00, -5.00, 2.00]
c //= 2.1       -> [0.00, -3.00, 0.00]
c //= [6, 2, 8] -> [0.00, -2.00, 0.00]

Examples of truediv:
a / d         -> [1.88, -3.40, 3.33]
a / 4         -> [1.50, -4.25, 2.00]
a / 2.1       -> [2.86, -8.10, 3.81]
a / [3, 10, 3] -> [2.00, -1.70, 2.67]

Examples of inplace truediv:
c /= d         -> [1.88, -3.40, 3.33]
c /= 4         -> [1.50, -4.25, 2.00]
c /= 2.1       -> [0.71, -2.02, 0.95]
c /= [6, 2, 8] -> [0.12, -1.01, 0.12]

Examples of matmul (cross product):
[6.00, -17.00, 8.00]
[3.00, 0.00, 3.00]
a @ b          -> [-51.00, 6.00, 51.00]
a.dot(a @ b)   -> 0
a @ [3, 10, 3] -> [-131.00, 6.00, 111.00]

Examples of inplace matmul (cross product):
c @= b         -> [-51.00, 6.00, 51.00]
c @= [6, 0, 8] -> [-136.00, 0.00, 102.00]

Example of right side matmul for transformation matricies
TRANSFORM @ a -> [ -6.   8. -17.]

Examples of equality:
a == e           -> True
a == e + 1       -> False
a == [6, -17, 8] -> True
a == [7, -16, 9] -> False

Examples of not equality:
a != e           -> False
a != e + 1       -> True
a != [6, -17, 8] -> False
a != [7, -16, 9] -> True

Examples of less than:
a < e           -> False
a < e + 1       -> False
a < e - 1       -> True
a < [6, -17, 8] -> False
a < [7, -16, 9] -> False
a < [5, -18, 7] -> True

Examples of greater than:
a > e           -> False
a > e + 1       -> True
a > e - 1       -> False
a > [6, -17, 8] -> False
a > [7, -16, 9] -> True
a > [5, -18, 7] -> False

Examples of less than or equal:
a <= e           -> True
a <= e + 1       -> False
a <= e - 1       -> True
a <= [6, -17, 8] -> True
a <= [7, -16, 9] -> False
a <= [5, -18, 7] -> True

Examples of greater than or equal:
a >= e           -> True
a >= e + 1       -> True
a >= e - 1       -> False
a >= [6, -17, 8] -> True
a >= [7, -16, 9] -> True
a >= [5, -18, 7] -> False

Examples of Point.reduce:
a.reduce() -> -3 from [6.00, -17.00, 8.00]
b.reduce() -> 6 from [3.00, 0.00, 3.00]
c.reduce() -> -34 from [-136.00, 0.00, 102.00]
d.reduce() -> 10.6 from [3.20, 5.00, 2.40]
e.reduce() -> -3 from [6.00, -17.00, 8.00]

Examples of Point.radius:
a.radius()     -> 19.72308292331602 from [6.00, -17.00, 8.00]
b.radius()     -> 4.242640687119285 from [3.00, 0.00, 3.00]
c.radius()     -> 170.0 from [-136.00, 0.00, 102.00]
d.radius()     -> 6.4031242374328485 from [3.20, 5.00, 2.40]
e.radius()     -> 19.72308292331602 from [6.00, -17.00, 8.00]
zeros.radius() -> 0.0 from [0.00, 0.00, 0.00]

Examples of Point.unitize:
a.unitize()     -> [0.30, -0.86, 0.41] from [6.00, -17.00, 8.00]
b.unitize()     -> [0.71, 0.00, 0.71] from [3.00, 0.00, 3.00]
c.unitize()     -> [-0.80, 0.00, 0.60] from [-136.00, 0.00, 102.00]
d.unitize()     -> [0.50, 0.78, 0.37] from [3.20, 5.00, 2.40]
e.unitize()     -> [0.30, -0.86, 0.41] from [6.00, -17.00, 8.00]
zeros.unitize() -> [0.00, 0.00, 0.00] from [0.00, 0.00, 0.00]

Examples of Point.as_list:
a.as_list()     -> [6, -17, 8] from [6.00, -17.00, 8.00]
b.as_list()     -> [3, 0, 3] from [3.00, 0.00, 3.00]
c.as_list()     -> [-136, 0, 102] from [-136.00, 0.00, 102.00]
d.as_list()     -> [3.2, 5.0, 2.4] from [3.20, 5.00, 2.40]
e.as_list()     -> [6, -17, 8] from [6.00, -17.00, 8.00]
zeros.as_list() -> [0, 0, 0] from [0.00, 0.00, 0.00]

Examples of Point.as_array:
a.as_array()     -> [  6 -17   8] from [6.00, -17.00, 8.00]
b.as_array()     -> [3 0 3] from [3.00, 0.00, 3.00]
c.as_array()     -> [-136    0  102] from [-136.00, 0.00, 102.00]
d.as_array()     -> [3.2 5.  2.4] from [3.20, 5.00, 2.40]
e.as_array()     -> [  6 -17   8] from [6.00, -17.00, 8.00]
zeros.as_array() -> [0 0 0] from [0.00, 0.00, 0.00]

Examples of Point.from_list:
Point.from_list([6, 0, 8]) -> [6.00, 0.00, 8.00]
Point.from_list([3, 0, 3]) -> [3.00, 0.00, 3.00]
```

---

# License

See [SolTrace licence](https://github.com/NLR-SolTrace/SolTrace-Examples/blob/main/LICENSE.md).