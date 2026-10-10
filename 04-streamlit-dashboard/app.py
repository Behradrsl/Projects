"""Generate passwords through a Streamlit interface."""

import re

import streamlit as st

from password_generators import (
    MemorablePasswordGenerator,
    PinCodeGenerator,
    RandomPasswordGenerator,
)

st.set_page_config(page_title="Password Generator", page_icon="🔑", layout="centered")
st.title("Password Generator")
st.write("Choose a type, adjust the options, and generate a password.")

kind = st.radio("Password type", ["Random password", "Memorable password", "PIN code"])

with st.form("generator"):
    if kind == "Random password":
        length = st.slider("Password length", 8, 128, 16)
        numbers = st.checkbox("Include numbers", value=True)
        symbols = st.checkbox("Include symbols", value=True)
    elif kind == "Memorable password":
        count = st.slider("Number of words", 3, 12, 4)
        separator = st.text_input("Separator", value="-", max_chars=3)
        capitalize = st.checkbox("Capitalize each word")
        custom = st.text_area(
            "Your own words (optional)",
            placeholder="river, cloud, forest, stone",
            help=(
                "Separate words with commas, spaces, or new lines. "
                "Leave blank for the built-in list."
            ),
        )
    else:
        length = st.slider("PIN length", 4, 12, 6)
    submitted = st.form_submit_button("Generate", type="primary")

if submitted:
    try:
        if kind == "Random password":
            generator = RandomPasswordGenerator(length, numbers, symbols)
        elif kind == "Memorable password":
            vocabulary = re.split(r"[\s,]+", custom.strip()) if custom.strip() else None
            generator = MemorablePasswordGenerator(count, separator, capitalize, vocabulary)
        else:
            generator = PinCodeGenerator(length)
        st.session_state["result"] = {"kind": kind, "value": generator.generate()}
    except ValueError as exc:
        st.session_state.pop("result", None)
        st.error(str(exc))

result = st.session_state.get("result")
if result and result["kind"] == kind:
    st.subheader("Last generated result")
    st.code(result["value"], language=None, wrap_lines=True)
    st.caption("Use the copy button in the result box. Press Generate for another result.")
else:
    st.info("Choose your settings and press Generate to see a result.")

with st.expander("How it works"):
    st.write(
        "Random passwords include upper- and lowercase letters and each enabled character type. "
        "Memorable passwords join independently selected words; repeats are possible. "
        "PINs contain only digits and can start with zero."
    )
    st.write(
        "The app does not save results to a file or database. The last result stays in this "
        "browser session. The built-in word list works without a download; a small word list "
        "or short PIN offers fewer possible combinations."
    )
