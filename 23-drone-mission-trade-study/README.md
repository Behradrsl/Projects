# Drone mission trade study

Compare inspection-drone configurations using mission requirements, usable battery energy and explicit cost versus endurance preferences.

## Run it

Requires **Python 3.10 or newer**. No API keys or external services are needed.

```bash
cd 23-drone-mission-trade-study
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate`. The launcher uses the project's `.venv` when available. In VS Code, open `main.py` and choose **Run Python File in Terminal**. Open the local URL printed in the terminal. Stop with Ctrl+C. Use `python main.py --server.port 8502` if the default port is busy.

## Try a trade study

The synthetic Scout, Surveyor and Carrier candidates have editable battery energy, average power, payload capacity and cost. The default mission requires 20 minutes, a 0.6 kg payload, a €3,000 budget and 20% battery reserve. Surveyor is the only feasible default alternative: predicted usable endurance is about 27.08 minutes, payload margin 0.3 kg and budget margin €800. Scout fails payload capacity; Carrier exceeds budget.

Increase the budget to €4,000 to include Carrier, then explore the preference sensitivity chart. Raise required time to 45 minutes to see the no-feasible-alternative state. Add or delete candidate rows in the editor.

## How it works

`trade.py` calculates endurance in minutes as `60 × battery Wh × (1 − reserve) / average power W`. All three constraint margins must be nonnegative before a candidate receives a score.

The preference score is `100 × [w × min(endurance / (2 × required time), 1) + (1 − w) × (1 − cost / budget)]`, where w ranges from 0 to 1. Fixed mission-relative scales avoid score changes caused only by adding another alternative. Ties preserve input order. The sensitivity chart recalculates scores at 11 preference weights. Infeasible candidates remain unscored.

Download `trade_study.json` for mission assumptions and results, or `trade_results.csv` for a comparison table. Blank CSV scores and JSON null mean infeasible.

## Limits

All candidate values are illustrative assumptions, not manufacturer specifications. Average power must correspond to the actual payload and operating conditions; this app does not infer payload effects, weather, battery aging or peak power. The weighted score expresses preferences and is not a success probability. Tests check analytical endurance, exact constraint boundaries, infeasible cases and preference changes.

Reference: [NASA Systems Engineering Handbook appendix: trade study and verification terminology](https://www.nasa.gov/reference/system-engineering-handbook-appendix/).

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

`main.py` launches the browser interface, `app.py` renders the views and the domain module holds the calculations. Tests run offline, including Streamlit interaction checks.
