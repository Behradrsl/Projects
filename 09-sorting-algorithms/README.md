# Sorting Algorithms

Sort whole numbers with bubble sort, insertion sort, and selection sort. Compare their results and measured running times on the same input.

## Run it

Python 3.10 or newer. No packages are needed.

```bash
cd 09-sorting-algorithms
python3 main.py
```

Enter numbers separated by spaces or commas, such as `8, 3, -1, 3`. All three algorithms return `[-1, 3, 3, 8]`. Negative numbers and repeated values are supported. Type `q` at the prompt to exit.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. On Windows, use `py main.py`.

You can also pass numbers directly:

```bash
python3 main.py 8 3 -1 3
python3 main.py 8 3 -1 3 --algorithm insertion
python3 main.py --random 100 --seed 42
```

`--random` generates between 1 and 2,000 numbers. `--seed` makes that input repeatable. The 2,000-number limit keeps the quadratic algorithms practical to run.

## How the algorithms work

| Algorithm | Method | Best time | Average / worst time | Stable |
| --- | --- | --- | --- | --- |
| Bubble sort | Swap adjacent out-of-order values; stop when a pass makes no swaps. | O(n) | O(n²) | Yes |
| Insertion sort | Insert each value into the sorted section on its left. | O(n) | O(n²) | Yes |
| Selection sort | Find the smallest remaining value and move it into place. | O(n²) | O(n²) | No |

The functions in `sorting.py` return a new list and leave your input unchanged. Sorting the working copy needs O(1) auxiliary space; making that copy requires O(n) additional space. Bubble and insertion sort preserve the order of equal values; selection sort can change it.

`main.py` runs each selected algorithm five times and prints the median elapsed time in milliseconds. Each run starts with the same original values. These timings describe one execution environment; they do not calculate complexity or establish that one algorithm is always fastest. For normal application code, Python's built-in `sorted()` is usually the practical choice.

To use a function yourself, from this folder:

```python
from sorting import insertion_sort

values = [8, 3, -1, 3]
print(insertion_sort(values))  # [-1, 3, 3, 8]
print(values)                 # [8, 3, -1, 3]
```

## Checks

```bash
python3 -m unittest discover -s tests -v
```

Tests compare every algorithm with `sorted()` on empty, ordered, reversed, repeated, negative, and seeded random inputs. They also check input preservation, argument errors, and terminal usage.

Optional style checks:

```bash
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
```
