"""Explore a linked architecture and its verification gaps."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from model import diagram, impact, traceability, validate

st.set_page_config(page_title="MBSE traceability explorer", layout="wide")
st.title("MBSE traceability explorer")
st.caption(
    "One inspection-drone model. Architecture, requirements and "
    "verification views derived from the same links."
)
example = (Path(__file__).parent / "examples/inspection_drone.json").read_text()
with st.sidebar:
    st.header("Engineering model")
    st.caption(
        "Edit the JSON or load your own model. Test statuses are recorded "
        "examples, not executed tests."
    )
    uploaded = st.file_uploader("Load JSON model", type=["json"])
    if uploaded is not None:
        if uploaded.size > 200000:
            st.error("Model upload must be under 200 KB.")
            st.stop()
        try:
            example = uploaded.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            st.error("Use a UTF-8 JSON file.")
            st.stop()
    source = st.text_area("Model JSON", example, height=350, max_chars=200000)
try:
    model = json.loads(source)
    elements = validate(model)
except (ValueError, TypeError) as exc:
    st.error(f"Model needs correction: {exc}")
    st.stop()
rows = traceability(model)
covered = sum(r["Link coverage"] for r in rows)
with st.container(horizontal=True):
    st.metric("Model elements", len(elements))
    st.metric("Requirements with both links", f"{covered}/{len(rows)}")
    st.metric(
        "Recorded passing requirements",
        sum(r["Recorded test outcome"] == "pass" for r in rows),
    )
st.subheader("Architecture and trace links")
st.graphviz_chart(
    diagram(model),
    width="stretch",
    alt="Architecture graph linking requirements, components, interfaces and tests",
)
st.subheader("Requirement traceability")
if rows:
    st.dataframe(
        rows,
        hide_index=True,
        alt="Requirement allocation and recorded verification outcomes",
    )
else:
    st.info("The model has no requirements. Add requirement elements and trace links.")
if covered < len(rows):
    st.warning(
        "Some requirements are missing an allocation or verification link. "
        "Link coverage does not establish requirement satisfaction."
    )
st.subheader("Change impact")
components = [e["id"] for e in elements.values() if e["kind"] == "component"]
if components:
    selected = st.selectbox(
        "Changed component",
        components,
        format_func=lambda key: f"{key}: {elements[key]['name']}",
    )
    affected = impact(model, selected)
    st.dataframe(
        [
            {"Category": k, "Review these elements": ", ".join(v) or "None"}
            for k, v in affected.items()
        ],
        hide_index=True,
        alt="Elements to review after the selected component changes",
    )
    st.caption(
        "Impact follows reverse depends_on links transitively, then "
        "allocations, verification links and attached interfaces. It does not "
        "propagate through interfaces or infer unmodeled dependencies."
    )
else:
    affected = {}
    st.info("Add a component to explore change impact.")
st.download_button(
    "Download model",
    json.dumps(model, indent=2),
    "engineering_model.json",
    "application/json",
)
st.download_button(
    "Download traceability CSV",
    pd.DataFrame(rows).to_csv(index=False),
    "traceability.csv",
    "text/csv",
)
st.download_button(
    "Download review record",
    json.dumps({"traceability": rows, "impact": affected}, indent=2),
    "review_record.json",
    "application/json",
)
with st.expander("Model vocabulary"):
    st.markdown(
        "A component **satisfies** a requirement; a test **verifies** a "
        "requirement; an interface **connects** to a component; a component "
        "**depends_on** another component. These links are modeling "
        "assertions. The explorer checks identifier integrity and endpoint "
        "types. This small JSON metamodel is not SysML and does not execute "
        "tests, prove correctness or certify a design."
    )
