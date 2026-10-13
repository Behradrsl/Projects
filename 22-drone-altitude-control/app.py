"""Interactive altitude-control experiments."""

import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from control import Settings, simulate, summarize

st.set_page_config(page_title="Drone altitude control", layout="wide")
st.title("Drone altitude control lab")
st.caption(
    "Tune a vertical controller. Inspect its response to a downward gust "
    "at 12–16 seconds."
)
with st.sidebar:
    st.header("Experiment settings")
    kp = st.slider("Proportional gain (N/m)", 0.0, 12.0, 3.0, 0.1)
    ki = st.slider("Integral gain (N/(m·s))", 0.0, 4.0, 0.6, 0.1)
    kd = st.slider("Derivative gain (N·s/m)", 0.0, 12.0, 3.5, 0.1)
    target = st.slider("Target altitude (m)", 1.0, 25.0, 10.0)
    mass = st.slider("Mass (kg)", 0.5, 3.0, 1.5, 0.1)
    thrust = st.slider("Maximum thrust (N)", 5.0, 60.0, 30.0)
    wind = st.slider("Gust force (N)", -10.0, 10.0, -3.0)
    baseline = st.checkbox("Compare default gains", True)
s = Settings(
    kp=kp, ki=ki, kd=kd, target=target, mass=mass, max_thrust=thrust, disturbance=wind
)
rows = simulate(s)
metrics = summarize(rows, target)
if thrust <= mass * 9.81:
    st.warning(
        "Thrust cannot exceed weight. This configuration cannot climb to the target."
    )
with st.container(horizontal=True):
    for name in ["RMSE (m)", "Overshoot (m)", "Final error (m)"]:
        st.metric(name, f"{metrics[name]:.2f}")
df = pd.DataFrame(rows)
if baseline:
    default = Settings(target=target, mass=mass, max_thrust=thrust, disturbance=wind)
    df["Default gains (m)"] = [r["Altitude (m)"] for r in simulate(default)]
st.line_chart(
    df,
    x="Time (s)",
    y=["Altitude (m)", "Target (m)"] + (["Default gains (m)"] if baseline else []),
    y_label="Altitude (m)",
    alt="Altitude tracking with optional default-gain comparison",
)
st.line_chart(
    df,
    x="Time (s)",
    y=["Thrust (N)", "Wind force (N)"],
    y_label="Force (N)",
    alt="Commanded thrust and applied gust force",
)
st.dataframe([metrics], hide_index=True, alt="Control response metrics")
st.caption(
    "Recovery is measured from 16 s until altitude stays within max(2% of "
    "target, 0.1 m) through the end. Blank means it did not settle during "
    "this run."
)
st.download_button(
    "Download samples", df.to_csv(index=False), "altitude_samples.csv", "text/csv"
)
st.download_button(
    "Download experiment",
    json.dumps({"settings": asdict(s), "metrics": metrics}, indent=2),
    "experiment.json",
    "application/json",
)
with st.expander("Model and assumptions"):
    st.latex(r"m\ddot z = T - mg - 0.25\dot z + F_{gust}")
    st.markdown(
        "Hover feedforward plus PID; derivative on velocity; conditional "
        "integration prevents windup. Semi-implicit Euler uses a fixed 0.02 s "
        "step. Ground contact clamps altitude and downward velocity to zero. "
        "The point-mass model omits attitude, motor lag, sensor noise and "
        "battery dynamics. This is an educational simulation."
    )
