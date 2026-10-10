"""A small browser interface for currency conversions."""

import streamlit as st

from converter import CURRENCIES, convert_amount, get_exchange_rate, parse_amount

st.set_page_config(page_title="Currency Converter", page_icon="↔", layout="centered")
st.markdown(
    """<style>
    .stApp { font-family: 'Avenir Next', 'Trebuchet MS', sans-serif; }
    .block-container { max-width: 720px; padding-top: 3rem; }
    h1 { letter-spacing: -0.045em; }
    div[data-testid="stForm"] { background: white; }
    @media (max-width: 600px) { .block-container { padding-top: 1.5rem; } }
    </style>""",
    unsafe_allow_html=True,
)
st.title("Currency Converter")
st.write("Choose two currencies and see what your money converts to.")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rate(base, target):
    return get_exchange_rate(base, target)


codes = list(CURRENCIES)
with st.form("conversion_form"):
    amount_text = st.text_input(
        "Amount", value="100", help="Use a decimal point, without commas."
    )
    left, right = st.columns(2)
    base = left.selectbox(
        "From",
        codes,
        index=codes.index("EUR"),
        format_func=lambda code: f"{code} — {CURRENCIES[code]}",
    )
    target = right.selectbox(
        "To",
        codes,
        index=codes.index("USD"),
        format_func=lambda code: f"{code} — {CURRENCIES[code]}",
    )
    submitted = st.form_submit_button(
        "Convert", type="primary", use_container_width=True
    )

if submitted:
    st.session_state.pop("last_conversion", None)
    try:
        amount = parse_amount(amount_text)
        with st.spinner("Getting the exchange rate…"):
            rate = fetch_rate(base, target)
        result = convert_amount(amount, rate)
        st.session_state.last_conversion = (amount, rate, result)
    except (ValueError, RuntimeError) as error:
        st.error(str(error))

if "last_conversion" in st.session_state:
    amount, rate, result = st.session_state.last_conversion
    st.divider()
    st.caption(f"Last conversion: {amount:,f} {rate.base}")
    decimals = 0 if rate.target in ("JPY", "KRW") else 2
    st.subheader(f"{result:,.{decimals}f} {rate.target}")
    if rate.date:
        st.write(f"1 {rate.base} = {rate.value} {rate.target}")
        st.caption(f"Rate dated {rate.date} · Cached for up to one hour")
    else:
        st.caption(
            "The currencies match, so the exchange rate is 1. No rate lookup needed."
        )
else:
    st.caption("Your conversion will appear here.")

st.caption(
    "Daily reference rates from [Frankfurter](https://frankfurter.dev/). "
    "Banks and payment services may use different rates and charge fees."
)
