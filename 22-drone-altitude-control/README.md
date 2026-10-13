# Drone altitude control lab

Tune a PID controller for a vertical drone simulation, compare against default gains and export every time sample and experiment setting.

## Run it

Requires **Python 3.10 or newer**. No API keys or external services are needed.

```bash
cd 22-drone-altitude-control
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate`. The launcher uses the project's `.venv` when available. In VS Code, open `main.py` and choose **Run Python File in Terminal**. Open the local URL printed in the terminal. Stop with Ctrl+C. Use `python main.py --server.port 8502` if the default port is busy.

## Try an experiment

Start with the default gains and 10 m target. Increase proportional gain to see how the transient changes. Set maximum thrust to 10 N: the 1.5 kg drone cannot climb because its weight is 14.715 N. Reset thrust to 30 N and observe recovery after the −3 N gust applied from 12 to 16 s. The default-gain comparison uses the same plant, target and gust.

## How it works

`control.py` implements `m × acceleration = thrust − m × 9.81 − 0.25 × velocity + gust`. Thrust is hover feedforward plus proportional altitude error, integral error and negative derivative of measured altitude (velocity). Conditional integration limits windup at actuator bounds. Semi-implicit Euler advances velocity then position at 0.02 s intervals. Ground contact resets altitude and downward velocity to zero.

`app.py` displays altitude, thrust, root mean square tracking error, overshoot, final error and saturation percentage. Recovery time begins at the end of the gust (16 s) and requires all remaining samples to stay within max(2% of target, 0.1 m). A missing recovery value means the run did not settle within 30 s. RMSE includes the initial climb.

Downloads include `altitude_samples.csv` and `experiment.json`. Mass is in kg, distance in m, force in N and time in s. Gains therefore have units N/m, N/(m·s) and N·s/m.

## Limits

This educational point-mass model omits attitude, motor dynamics, sensor noise, battery depletion and aerodynamic coupling. It is a simulation study rather than flight software. The tests check hover equilibrium, thrust bounds, an impossible-climb case and integration-step consistency.

Reference: [University of Michigan control tutorials](https://ctms.engin.umich.edu/CTMS/).

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

`main.py` launches the browser interface, `app.py` renders the views and the domain module holds the calculations. Tests run offline, including Streamlit interaction checks.
