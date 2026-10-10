"""Review pasted text or a PDF without requiring an account for local checks."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from reviewer import ai_review, extract_pdf, local_review

root = Path(__file__).resolve().parent
load_dotenv(root / ".env")
st.set_page_config(page_title="Resume Auto Review", page_icon="▱")
st.title("Resume Auto Review")
st.write("Check your resume’s structure and wording, with an optional job description.")
method = st.radio("Resume input", ["Paste text", "Upload PDF"], horizontal=True)
text = ""
if method == "Paste text":
    text = st.text_area(
        "Resume text",
        value=(root / "sample_resume.txt").read_text(),
        height=280,
        max_chars=20000,
    )
    st.caption("The starting text is a fictional example. Replace it with your resume.")
else:
    upload = st.file_uploader("Text-based resume PDF", type=["pdf"])
    if upload:
        try:
            text = extract_pdf(upload.getvalue())
            with st.expander("Extracted text"):
                st.text(text)
        except ValueError as error:
            st.error(str(error))
with st.form("resume_options"):
    job = st.text_area("Job description (optional)", max_chars=12000)
    local = st.form_submit_button("Review locally", type="primary")
    ai = st.form_submit_button(
        "Review with AI", disabled=not bool(os.getenv("OPENAI_API_KEY"))
    )
st.caption(
    (
        "Local review stays on your computer. AI review sends the "
        "resume text and job description to OpenAI and uses paid API "
        "calls. Add OPENAI_API_KEY to .env to enable it."
    )
)
if local or ai:
    st.session_state.pop("resume_report", None)
    try:
        with st.spinner("Reviewing your resume…"):
            st.session_state.resume_report = (
                ai_review(text, job) if ai else local_review(text, job)
            )
    except (ValueError, RuntimeError) as error:
        st.error(str(error))
if "resume_report" in st.session_state:
    report = st.session_state.resume_report
    st.divider()
    st.markdown(report)
    st.download_button("Download review", report, "resume-review.md", "text/markdown")
