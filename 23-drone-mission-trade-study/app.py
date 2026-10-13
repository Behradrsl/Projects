"""Mission feasibility and preference exploration."""

import json

import pandas as pd
import streamlit as st

from trade import CANDIDATES, evaluate

st.set_page_config(page_title="Drone mission trade study", layout="wide")
st.title("Drone mission trade study")
st.caption(
    "Screen an inspection mission against engineering constraints, then "
    "rank the feasible alternatives."
)
with st.sidebar:
    st.header("Mission requirements")
    minutes = st.slider("Required flight time (min)", 5.0, 45.0, 20.0)
    payload = st.slider("Required payload (kg)", 0.1, 2.0, 0.6, 0.1)
    budget = st.number_input("Maximum cost (EUR)", 100.0, 10000.0, 3000.0, 100.0)
    reserve = st.slider("Battery reserve (%)", 0, 50, 20) / 100
    weight = st.slider("Endurance preference (%)", 0, 100, 50) / 100
st.subheader("Candidate configurations")
st.caption(
    "Synthetic configurations. Power must represent average draw at the "
    "selected payload and flight conditions."
)
edited = st.data_editor(
    pd.DataFrame(CANDIDATES),
    hide_index=True,
    num_rows="dynamic",
    key="candidates",
    alt="Editable drone configuration assumptions",
)
settings = dict(
    minutes=minutes,
    payload=payload,
    budget=budget,
    reserve=reserve,
    endurance_weight=weight,
)
try:
    results = evaluate(edited.to_dict("records"), **settings)
except (ValueError, TypeError, KeyError) as exc:
    st.error(f"Check candidate values: {exc}")
    st.stop()
feasible = [r for r in results if r["Feasible"]]
if feasible:
    st.success(
        f"Preferred feasible configuration: {feasible[0]['Name']} "
        f"(score {feasible[0]['Score']:.1f}/100). Ties retain input order."
    )
else:
    st.warning(
        "No configuration meets all three constraints. Review the negative "
        "margins below."
    )
df = pd.DataFrame(results)
st.subheader("Constraint margins and ranking")
st.dataframe(
    df, hide_index=True, alt="Feasibility, margins and scores for each candidate"
)
st.bar_chart(
    df, x="Name", y="Endurance (min)", alt="Predicted usable endurance by configuration"
)
st.subheader("Preference sensitivity")
sensitivity = []
for percent in range(0, 101, 10):
    for r in evaluate(
        edited.to_dict("records"), **{**settings, "endurance_weight": percent / 100}
    ):
        if r["Feasible"]:
            sensitivity.append(
                {
                    "Endurance preference (%)": percent,
                    "Configuration": r["Name"],
                    "Score": r["Score"],
                }
            )
if sensitivity:
    st.line_chart(
        pd.DataFrame(sensitivity),
        x="Endurance preference (%)",
        y="Score",
        color="Configuration",
        alt="Candidate scores across endurance versus cost preferences",
    )
st.download_button(
    "Download trade study",
    json.dumps(
        {"assumptions": settings, "results": results}, indent=2, allow_nan=False
    ),
    "trade_study.json",
    "application/json",
)
st.download_button(
    "Download results CSV", df.to_csv(index=False), "trade_results.csv", "text/csv"
)
with st.expander("Calculation and decision rules"):
    st.markdown(
        "Usable endurance = 60 × battery Wh × (1 − reserve) / average power "
        "W. All endurance, payload and cost margins must be nonnegative. "
        "Infeasible alternatives receive no score. Score = 100 × [w × "
        "min(endurance / (2 × required time), 1) + (1 − w) × (1 − cost / "
        "budget)]. Fixed scales keep candidate scores independent of the "
        "candidate set. Preference is subjective; the score is not a "
        "probability of mission success. Weather, battery aging and payload- "
        "dependent power are not modeled automatically."
    )
