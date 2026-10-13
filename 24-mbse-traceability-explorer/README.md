# MBSE traceability explorer

Explore a small inspection-drone architecture as a linked JSON model. Generate architecture, requirements traceability and component-change impact views from one source.

## Run it

Requires **Python 3.10 or newer**. No API keys or external services are needed.

```bash
cd 24-mbse-traceability-explorer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate`. The launcher uses the project's `.venv` when available. In VS Code, open `main.py` and choose **Run Python File in Terminal**. Open the local URL printed in the terminal. Stop with Ctrl+C. Use `python main.py --server.port 8502` if the default port is busy.

## Explore the example

The built-in model has four requirements. Three have both component allocations and verification links: link coverage is 3/4. The telemetry-loss requirement deliberately has neither. Of the three linked test records, one says pass, one fail and one not_run; the app does not execute these tests.

Select `C-NAV` as the changed component. The dependency chain includes `C-FC` and `C-CAM`, so altitude and image requirements, their verification cases and the navigation interface appear in the review list. Cyclic dependencies terminate safely.

Edit the sidebar JSON or upload a UTF-8 JSON file under 200 KB. Download the canonical model, traceability CSV or derived review record.

## Model vocabulary

Each element needs unique `id`, `kind` and `name` strings. Kinds are `requirement`, `component`, `test` and `interface`. Tests may have `status` set to `pass`, `fail` or `not_run` (the default). The root has `elements` and `links` arrays. Each link has exactly `source`, `target` and `kind`.

| Relationship | Source | Target | Meaning |
| --- | --- | --- | --- |
| satisfies | component | requirement | Claimed requirement allocation |
| verifies | test | requirement | Planned verification coverage |
| connects | interface | component | Attached interface |
| depends_on | component | component | Source depends on target |

`model.py` validates identifiers, endpoint types, duplicate links and model bounds (200 elements, 1,000 links). It derives one trace row per requirement. All linked tests must record pass for a row to say pass; any fail takes precedence, then not_run. No tests means unlinked. Link coverage requires both an allocated component and a verification case.

Change impact follows reverse depends_on links transitively, then finds allocated requirements, their verification cases and interfaces attached to affected components. It does not infer dependencies or propagate through interfaces. The graph uses the same source links as the matrix.

## Limits

The JSON format is a deliberately small metamodel, not SysML. Link coverage is distinct from test outcomes and engineering correctness. Statuses are user assertions without evidence execution. Interface direction, requirement refinement, formal behavior and version control are outside the model. Tests cover dangling references, relationship types, coverage, recorded outcomes and cyclic impact propagation.

Reference: [NASA Systems Engineering Handbook appendix: traceability and requirement verification](https://www.nasa.gov/reference/system-engineering-handbook-appendix/).

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

`main.py` launches the browser interface, `app.py` renders the views and the domain module holds the calculations. Tests run offline, including Streamlit interaction checks.
