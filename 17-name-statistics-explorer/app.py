"""Explore aggregate names in a CSV with regional counts."""

import csv
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from name_stats import load_records, summarize_name

st.set_page_config(page_title="Name Statistics Explorer", page_icon="▥")
st.title("Name Statistics Explorer")
st.write(
    "Explore how often a name appears in your data and how its counts vary by region."
)
upload = st.file_uploader(
    "Upload a CSV with name, region, and count columns", type=["csv"]
)
sample = (Path(__file__).resolve().parent / "sample.csv").read_bytes()
st.download_button(
    "Download example CSV", sample, "name-counts-example.csv", "text/csv"
)
if upload is None:
    st.caption("Showing fictional sample counts. These are not population statistics.")
try:
    records = load_records(upload.getvalue() if upload else sample)
    names = sorted(set(row["name"] for row in records), key=str.casefold)
    name = st.selectbox("Name", names)
    summary = summarize_name(records, name)
    st.subheader(
        f"{sum(row['count'] for row in summary):,} recorded occurrences of {name}"
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)
    st.bar_chart(pd.DataFrame(summary).set_index("region")["count"])
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["region", "count", "share_percent"])
    writer.writeheader()
    writer.writerows(summary)
    st.download_button(
        "Download summary", output.getvalue(), "name-summary.csv", "text/csv"
    )
except (ValueError, csv.Error) as error:
    st.error(str(error))
st.caption(
    (
        "Counts describe the supplied dataset. They do not predict a "
        "person’s origin, gender, or race. Uploaded data stays in "
        "this session."
    )
)
