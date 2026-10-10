"""Check a small list of websites and download the results."""

import csv
import io

import streamlit as st

from checker import check_sites

st.set_page_config(page_title="Site Connectivity Checker", page_icon="◉")
st.title("Site Connectivity Checker")
st.write(
    "Check whether your websites respond, and see their HTTP status and response time."
)
with st.form("sites_form"):
    text = st.text_area(
        "Websites, one per line",
        "https://www.python.org\nhttps://docs.python.org",
        height=160,
    )
    submitted = st.form_submit_button("Check websites", type="primary")
if submitted:
    st.session_state.pop("site_results", None)
    try:
        urls = [line.strip() for line in text.splitlines() if line.strip()]
        with st.spinner("Checking websites…"):
            st.session_state.site_results = [
                result.as_dict() for result in check_sites(urls)
            ]
    except ValueError as error:
        st.error(str(error))
if "site_results" in st.session_state:
    results = st.session_state.site_results
    st.dataframe(results, hide_index=True, use_container_width=True)
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["url", "status", "code", "milliseconds", "detail"]
    )
    writer.writeheader()
    writer.writerows(results)
    st.download_button(
        "Download results as CSV", output.getvalue(), "site-results.csv", "text/csv"
    )
st.caption(
    (
        "Checks run when you click the button. A 403 or 404 means the"
        " server responded with an HTTP error; it does not prove the "
        "server is offline."
    )
)
