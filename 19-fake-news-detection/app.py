"""Review a claim with an evidence checklist or sourced web research."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from news_review import evidence_checklist, review_claim

load_dotenv(Path(__file__).resolve().parent / ".env")
st.set_page_config(page_title="News Claim Review", page_icon="▤")
st.title("News Claim Review")
st.write("Check the evidence behind a headline or a specific news claim.")
mode = st.radio("Review method", ["Manual checklist", "AI web review"], horizontal=True)
if mode == "AI web review":
    st.caption(
        (
            "AI web review sends your claim to OpenAI and searches for "
            "current sources. It requires an API key and uses paid API "
            "calls."
        )
    )
    if not os.getenv("OPENAI_API_KEY"):
        st.info(
            (
                "Add OPENAI_API_KEY to this project’s .env file. The manual "
                "checklist works without a key."
            )
        )
with st.form("claim_form"):
    claim = st.text_area(
        "Claim to review",
        placeholder="Include the event, place, and date when known.",
        max_chars=1500,
    )
    checks = {}
    if mode == "Manual checklist":
        for label in [
            "Find the original source",
            "Check the publication and event dates",
            "Read beyond the headline",
            "Compare independent reporting",
        ]:
            checks[label] = st.checkbox(label)
    submitted = st.form_submit_button("Review claim", type="primary")
if submitted:
    st.session_state.pop("news_report", None)
    try:
        with st.spinner("Reviewing the claim…"):
            if mode == "Manual checklist":
                report = evidence_checklist(claim, checks)
                sources = []
            else:
                result = review_claim(claim)
                report, sources = result.text, result.sources
        st.session_state.news_report = (report, sources)
    except (ValueError, RuntimeError) as error:
        st.error(str(error))
if "news_report" in st.session_state:
    report, sources = st.session_state.news_report
    st.divider()
    st.markdown(report)
    if sources:
        st.subheader("Sources to inspect")
        for source in sources:
            st.link_button(source["title"], source["url"])
    st.download_button("Download review", report, "news-review.md", "text/markdown")
st.caption(
    (
        "An AI assessment can be wrong. Inspect the cited evidence "
        "before sharing a conclusion."
    )
)
