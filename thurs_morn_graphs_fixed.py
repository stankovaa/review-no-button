import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import smtplib
import csv
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from calcs import (
    generate_exit_values,
    compute_sell_today_proceeds,
    compute_founder_proceeds,
    apply_risk,
    compute_desired_proceeds,
    compute_callout_values,
)

import streamlit as st

st.set_page_config(page_title="Founder Proceeds", layout="wide")

st.markdown(
    """
    <style>
      /* App background (main area) */
      .stApp {
        background: "rgb(24,28,41)";  /* pick your dark color */
        color: #ffffff;
      }

      /* Main content container */
      [data-testid="stAppViewContainer"] {
        background: #0b1220;
      }

      /* Sidebar background */
      [data-testid="stSidebar"] {
        background: #0b1220;
      }

      /* Sidebar inner content */
      [data-testid="stSidebarContent"] {
        background: #0b1220;
      }

      /* Top header bar */
      [data-testid="stHeader"] {
        background: #0b1220;
      }

      /* Optional: reduce the “white gap” around blocks */
      .block-container {
        padding-top: 1rem;
        max-width: 1240px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)    
    
# --- Trachet brand colors
PAGE_BG = "#0b1220"
SECONDARY_COLOR = "rgb(0,102,253)"
GRAPH_YELLOW = "rgb(255,236,0)"
GRAPH_CYAN = "rgb(44,244,255)"
GRAPH_GREEN = "rgb(44,253,13)"
GRAPH_PURPLE = "rgb(211,176,255)"
TEXT_COLOR = "rgb(255,255,255)"
PLOT_COLOR = "rgb(172,176,179)"
PLOT_FONT = "Poppins"

# --- Custom CSS for branding
st.set_page_config(page_title="Founder Proceeds Calculator", layout="wide", initial_sidebar_state="expanded")

custom_css = f"""
<style>
    /* Main background and text */
    .stApp {{
        background-color: {PAGE_BG};
        color: {TEXT_COLOR};
    }}
    
    /* Sidebar styling — fixed width, no user resize */
    section[data-testid="stSidebar"] {{
        background-color: {PAGE_BG};
        color: {TEXT_COLOR};
        width: 260px !important;
        min-width: 260px !important;
        max-width: 260px !important;
    }}
    div[data-testid="stSidebarResizeHandle"] {{
        display: none !important;
        pointer-events: none !important;
    }}

    /* Responsive chart columns — stack vertically when screen too narrow */
    section.main [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
    }}
    section.main [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        min-width: 600px !important;
        flex: 1 1 600px !important;
    }}

    /* Model Assumptions expander label */
    section[data-testid="stSidebar"] details summary p,
    section[data-testid="stSidebar"] details summary span {{
        font-size: 12px !important;
        color: #ffffff !important;
    }}

    /* Help tooltip icon — white circle, dark fill, white ? */
    section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg circle {{
        fill: {PAGE_BG} !important;
        stroke: #ffffff !important;
        stroke-width: 1.5 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg path {{
        fill: #ffffff !important;
    }}
    
    /* --- FIX: force all widget labels to white --- */
    label[data-testid="stWidgetLabel"] {{
        color: {TEXT_COLOR} !important;
    }}

    /* Text color overrides */
    .stMarkdown {{
        color: {TEXT_COLOR};
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT_COLOR};
    }}
    
    /* Selectbox and input styling */
    .stSelectbox [data-testid="stSelectbox"] label {{
        color: {TEXT_COLOR};
    }}
    
    .stSlider label {{
        color: {TEXT_COLOR};
    }}
    
    .stTextInput label {{
        color: {TEXT_COLOR};
    }}
    
    /* Button styling */
    .stButton > button {{
        background-color: {SECONDARY_COLOR};
        color: {TEXT_COLOR};
        border: none;
    }}
    
    .stButton > button:hover {{
        background-color: {SECONDARY_COLOR};
        opacity: 0.8;
    }}
    
    /* Expander styling */
    .streamlit-expanderHeader {{
        color: {TEXT_COLOR};
    }}
    
    /* Divider */
    hr {{
        border-color: {SECONDARY_COLOR};
    }}
    
    /* --- Select slider + slider: value text above the thumb --- */
    div[data-testid="stSelectSlider"] [data-testid="stThumbValue"],
    div[data-testid="stSlider"]      [data-testid="stThumbValue"] {{
        color: {SECONDARY_COLOR} !important;  /* rgb(0,102,253) */
    }}
    
    /* --- Select slider + slider: the draggable thumb (dot) --- */
    div[data-testid="stSelectSlider"] div[data-baseweb="slider"] div[role="slider"],
    div[data-testid="stSlider"]      div[data-baseweb="slider"] div[role="slider"] {{
        background-color: {SECONDARY_COLOR} !important;
        border-color: {SECONDARY_COLOR} !important;

        /* optional: blue glow ring */
        box-shadow: 0 0 0 0.2rem rgba(0, 102, 253, 0.25) !important;
    }}

    /* --- Callout boxes (styled like Plotly legend) --- */
    .trachet-callout {{
        border: 5px solid rgb(0,102,253);     /* SECONDARY_COLOR */
        background: rgba(0,0,0,0.5);          /* like legend bgcolor */
        color: rgb(255,255,255);              /* TEXT_COLOR */
        padding: 12px 14px;
        border-radius: 0px;
        font-family: Poppins, sans-serif;     /* PLOT_FONT */
        font-size: 16px;
        line-height: 1.35;
        min-height: 84px;
        display: flex;
        align-items: center;
    }}
    .trachet-callout-row {{
        display: flex;
        gap: 12px;
        align-items: stretch;   /* <-- makes all boxes equal height */
    }}

    .trachet-callout {{
        flex: 1;                /* <-- equal widths */
        border-radius: 0px;     /* sharp corners */
        /* keep your existing styles (border, bg, color, padding, etc.) */
    }}
    .trachet-callout p {{ margin: 0; }}
   /* highlight for $m */
    .trachet-highlight {{
        color: rgb(0,102,253);
        font-weight: 700;
        white-space: nowrap; /* keeps $m together */
    }}

    /* prevent default <p> margins inside the callout */
    .trachet-callout p {{
        margin: 0;
    }}
    /* --- Compact sidebar --- */

    /* Labels and markdown text */
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] label,
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] span,
    section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] .stMarkdown p {{
        font-size: 12px !important;
        line-height: 1.1 !important;
        margin-bottom: 0 !important;
    }}

    /* Headings */
    section[data-testid="stSidebar"] h1 {{
        font-size: 14px !important;
        margin: 2px 0 4px !important;
        padding-bottom: 0 !important;
    }}
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        font-size: 12px !important;
        margin: 0px 0 0px !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}

    /* Selectbox — shrink the control box */
    section[data-testid="stSidebar"] div[data-baseweb="select"],
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
        min-height: 24px !important;
        height: 24px !important;
        overflow: visible !important;
    }}
    /* Value container: flex-center so text isn't clipped */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        display: flex !important;
        align-items: center !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div > div {{
        display: flex !important;
        align-items: center !important;
        overflow: hidden !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
        font-size: 12px !important;
        line-height: 1.1 !important;
    }}

    /* Number input — shrink all wrapper levels */
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"],
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input-container"],
    section[data-testid="stSidebar"] div[data-baseweb="input"] {{
        min-height: 24px !important;
        height: 24px !important;
    }}
    section[data-testid="stSidebar"] input[type="number"] {{
        font-size: 12px !important;
        padding: 1px 4px !important;
        height: 24px !important;
    }}
    /* Step buttons (+ / -) inside number input */
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button {{
        height: 12px !important;
        min-height: 12px !important;
        font-size: 11px !important;
        padding: 0 !important;
    }}

    /* Text input (disabled fields) */
    section[data-testid="stSidebar"] div[data-baseweb="base-input"] {{
        min-height: 24px !important;
        height: 24px !important;
    }}
    section[data-testid="stSidebar"] input[type="text"] {{
        font-size: 12px !important;
        padding: 1px 6px !important;
        height: 24px !important;
    }}

    /* Reduce column horizontal padding */
    section[data-testid="stSidebar"] div[data-testid="column"] {{
        padding-left: 2px !important;
        padding-right: 2px !important;
    }}

    /* Overall widget vertical spacing */
    section[data-testid="stSidebar"] .stSelectbox,
    section[data-testid="stSidebar"] .stNumberInput,
    section[data-testid="stSidebar"] .stSlider,
    section[data-testid="stSidebar"] .stTextInput {{
        margin-bottom: -10px !important;
    }}

    /* Slider track */
    section[data-testid="stSidebar"] div[data-baseweb="slider"] {{
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }}

    /* Slider — all text inside (thumb value, tick labels, any span/p/div) */
    section[data-testid="stSidebar"] div[data-testid="stSlider"] *,
    section[data-testid="stSidebar"] div[data-testid="stThumbValue"],
    section[data-testid="stSidebar"] div[data-testid="stThumbValue"] *,
    section[data-testid="stSidebar"] div[data-testid="stTickBar"],
    section[data-testid="stSidebar"] div[data-testid="stTickBar"] *,
    section[data-testid="stSidebar"] div[data-baseweb="slider"] *,
    section[data-testid="stSidebar"] [data-testid="stSlider"] p,
    section[data-testid="stSidebar"] [data-testid="stSlider"] span {{
        font-size: 12px !important;
        line-height: 1.1 !important;
    }}

    /* Disclaimer text — only targets the dedicated disclaimer class */
    section[data-testid="stSidebar"] .sidebar-disclaimer {{
        font-size: 9px !important;
        line-height: 1.2 !important;
    }}


    /* --- CTA button styled like the callout boxes (secondary buttons only) --- */
    div[data-testid="stButton"] > button[kind="secondary"] {{
    border: 1px solid rgb(0,102,253) !important;
    background: rgba(0,0,0,0.5) !important;
    color: rgb(255,255,255) !important;
    border-radius: 0px !important;          /* sharp corners */
    padding: 12px 14px !important;
    font-family: Poppins, sans-serif !important;
    font-size: 14px !important;
    line-height: 1.35 !important;
    text-align: left !important;
    width: 100% !important;
    }}

    div[data-testid="stButton"] > button[kind="secondary"]:hover {{
    background: rgba(0,102,253,0.15) !important;
    }}

    div[data-testid="stButton"] > button[kind="secondary"]:focus {{
    box-shadow: 0 0 0 0.2rem rgba(0,102,253,0.25) !important;
    }}

    /* --- Welcome dialog --- */
    div[data-testid="stDialog"] > div,
    div[data-testid="stDialog"] [data-baseweb="modal"],
    div[data-testid="stModal"] > div,
    div[role="dialog"] {{
        background-color: {PAGE_BG} !important;
        border: 2px solid {SECONDARY_COLOR} !important;
        color: #ffffff !important;
    }}
    div[role="dialog"] *,
    div[data-testid="stDialog"] * {{
        color: #ffffff !important;
    }}
    /* Dialog close button */
    div[role="dialog"] button[aria-label="Close"],
    div[data-testid="stDialog"] button[aria-label="Close"] {{
        color: #ffffff !important;
        background: transparent !important;
    }}

</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# --- Welcome dialog (shown once per session) --------------------------------
@st.dialog("Welcome to Trachet's Founder Proceeds Calculator")
def welcome_dialog():
    st.markdown(
        "This tool is designed to help founders model the economic impact of "
        "raising a new round before a strategic exit - versus selling today.\n\n"
        "Enter your assumptions in the sidebar to explore your personalised scenarios. "
        "For a detailed analysis of your specific cap table, reach out to our team at "
        "[hello@trachet.co](mailto:hello@trachet.co).\n\n"
    )
    st.markdown(
        "<p style='font-size:10px;opacity:0.7;'><em>This calculator is provided for indicative "
        "purposes only and does not constitute financial or investment advice. Results are based "
        "solely on user-entered assumptions and a number of simplifying model assumptions.</em></p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:11px;'>⚠️ <b>This app is best viewed on a desktop or laptop.</b></p>",
        unsafe_allow_html=True,
    )
    btn_col, logo_col = st.columns([3, 1])
    with btn_col:
        #st.markdown('<div style="margin-top:5px;"></div>', unsafe_allow_html=True)
        if st.button("Got it", use_container_width=True, type="primary"):
            st.rerun()
    with logo_col:
        import base64, pathlib
        _logo_b64 = base64.b64encode(pathlib.Path("Logo_white.png").read_bytes()).decode()
        st.markdown(
            f'<div style="display:flex;align-items:flex-end;height:100%;padding-bottom:10px;">'
            f'<img src="data:image/png;base64,{_logo_b64}" style="width:80%;max-width:80px;">'
            f'</div>',
            unsafe_allow_html=True,
        )

if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False

if not st.session_state.welcome_shown:
    st.session_state.welcome_shown = True
    welcome_dialog()

# --- Sidebar inputs --------------------------------------------------------
#st.sidebar.image("path/to/your_logo.png", use_container_width=True)
st.sidebar.title("Assumptions")
st.sidebar.markdown('<hr style="margin:4px 0 2px 0; border:none; border-top:1px solid #555;">', unsafe_allow_html=True)
st.sidebar.subheader("General Assumptions")
currency = st.sidebar.selectbox("Currency", ["$", "£", "€", "CHF"], index=0, key="currency")
rounds = ["Seed", "Series A", "Series B", "Series C", "Series D"]

last_round = st.sidebar.selectbox(
    "Last round name",
    rounds[:-1],
    index=2,
    key="last_round",
)

options1 = list(range(5_000_000, 200_000_000 + 1, 1_000_000))

last_post_money = st.sidebar.select_slider(
    "Last round post-money valuation",
    options=options1,
    value=30_000_000,
    format_func=lambda x: f"{currency}{x/1_000_000:.0f}m",
    key="last_post_money",
)

options2 = list(range(0, 100_000_000 + 1, 1_000_000))
options3 = list(range(5_000_000, 200_000_000 + 1, 1_000_000))

# Conditional fields for new round
show_new_bool = "Yes"

# Automatically set new round to one step above last round
new_round_name = rounds[rounds.index(last_round) + 1]

# Show it without allowing edits
st.sidebar.text_input(
    "New round name",
    value=new_round_name,
    disabled=True,
)
raise_goal = st.sidebar.select_slider(
    "Fundraising goal",
    options=options2,
    value=0_000_000.0,
    format_func=lambda x: f"{currency}{x/1_000_000:.0f}m",
    key="raise_goal",
)
pre_money = st.sidebar.select_slider(
    "New round pre-money valuation",
    options=options3,
    value=30_000_000.0,
    format_func=lambda x: f"{currency}{x/1_000_000:.0f}m",
    key="pre_money",
)
# else:
#     new_round_name = "N/A"
#     raise_goal = 0.0
#     pre_money = 0.0

liq_pref = st.sidebar.selectbox(
    "Investors have Liq Preference? ⁵",
    ["Yes", "No"],
    index=1,
    key="liq_pref",
    help="⁵ Historical investors are assumed to hold shares on equivalent terms to those selected for the new round above. See Model Assumptions for full details.",
)

# Conditional fields for preference type and cap
if liq_pref == "Yes":
    pref_type = st.sidebar.selectbox("Type of preference", ["Participating", "Non-Participating"], index=1, key="pref_type")
    if pref_type == "Participating":
        pref_cap = st.sidebar.selectbox(
            "Participating cap",
            ["1.00x", "1.50x", "2.00x", "2.50x", "3.00x", "3.50x", "4.00x", "4.50x", "5.00x", "5.50x", "6.00x"],
            index=2,
            key="pref_cap",
        )
        pref_multiple = float(pref_cap.replace("x", ""))
    else:
        pref_cap = "1.00x"
        pref_multiple = 1.0
else:
    pref_type = "Non-Participating"
    pref_cap = "1.00x"
    pref_multiple = 1.0

#risk_pct = st.sidebar.slider("Risk %", min_value=0.0, max_value=1.0, value=0.2, step=0.01)
risk_pct = 0.2

st.sidebar.markdown('<hr style="margin:4px 0 2px 0; border:none; border-top:1px solid #555;">', unsafe_allow_html=True)
st.sidebar.subheader("Ownership (%)")

# Input rows
label_col, input_col = st.sidebar.columns([3, 2])
with label_col:
    st.markdown('<div style="display:flex;align-items:center;height:24px;font-size:12px;">Founders</div>', unsafe_allow_html=True)
with input_col:
    founders_pct = st.number_input(
        "Founders",
        min_value=0.0,
        max_value=100.0,
        value=50.0,
        step=0.1,
        format="%.1f",
        label_visibility="collapsed",
        key="founders_pct",
    )

label_col, input_col = st.sidebar.columns([3, 2])
with label_col:
    st.markdown('<div style="display:flex;align-items:center;height:24px;font-size:12px;">Historical investors</div>', unsafe_allow_html=True)
with input_col:
    historical_pct = st.number_input(
        "Historical investors",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=0.1,
        format="%.1f",
        label_visibility="collapsed",
        key="historical_pct",
    )

label_col, input_col = st.sidebar.columns([3, 2])
with label_col:
    st.markdown('<div style="display:flex;align-items:center;height:24px;font-size:12px;">New investors</div>', unsafe_allow_html=True)
with input_col:
    new_pct = st.number_input(
        "New investors",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        format="%.1f",
        label_visibility="collapsed",
        key="new_pct",
    )

# Computed fields
other_pct = max(0.0, 100.0 - founders_pct - historical_pct - new_pct)
total_pct = founders_pct + historical_pct + new_pct + other_pct

label_col, input_col = st.sidebar.columns([3, 2])
with label_col:
    st.markdown('<div style="display:flex;align-items:center;height:24px;font-size:12px;">Others</div>', unsafe_allow_html=True)
with input_col:
    st.text_input(
        "Other investors",
        value=f"{other_pct:.1f}",
        disabled=True,
        label_visibility="collapsed",
    )

label_col, input_col = st.sidebar.columns([3, 2])
with label_col:
    st.markdown('<div style="display:flex;align-items:center;height:24px;font-size:12px;font-weight:bold;">Total</div>', unsafe_allow_html=True)
with input_col:
    st.markdown(f'<div style="display:flex;align-items:center;height:24px;font-size:12px;font-weight:bold;background-color:#000000;color:#ffffff;padding:0 8px;border-radius:4px;">{total_pct:.1f}</div>', unsafe_allow_html=True)
st.sidebar.markdown('<hr style="margin:2px 0 4px 0; border:none; border-top:1px solid #555;">', unsafe_allow_html=True)

if founders_pct + historical_pct + new_pct > 100.0:
    st.sidebar.error("Ownership exceeds 100%. Please reduce Founders, Historical investors, or New investors.")

exit_base = pre_money*3
#exit_base = st.sidebar.number_input("Target exit valuation", value=150_000_000.0, min_value=0.0, format="%.0f")

# parse booleans and numeric prefs
#show_new_bool = show_new == "Yes"
liq_pref_bool = liq_pref == "Yes"

# --- after your sidebar inputs ---
#st.sidebar.markdown("---")

with st.sidebar.expander("Model Assumptions"):
    st.markdown(
        """
        <div style="font-size: 11px; color: rgb(255,255,255); line-height: 1.35;">
            1. Liquidation preference multiples are assumed at 1.0x for all preferred share classes.<br>
            2. "Others" represents the aggregate residual ownership of all remaining cap table participants, including angel investors, ESOPs, advisors, and other minority shareholders.<br>
            3. "Sell today" scenario assumes exit valuation equal to the pre-money valuation of the prospective new round.<br>
            4. All investor classes are treated <i>pari passu</i>, with proceeds allocated pro rata to total invested capital.<br>
            5. Historical investors are assumed to hold shares on equivalent terms to those selected for the new round above.<br>
            6. All proceeds are presented on a pre-tax basis. Tax treatment — including capital gains tax, entrepreneurs' relief, and jurisdiction-specific considerations — is excluded and may materially affect net proceeds.<br>
            7. The exit valuation range is automatically generated at 0.25x–4.0x the post-money valuation of the prospective new round. <br>
            8. The Risk-Adjusted curve applies a fixed 20% discount to the 'Raise & Sell' scenario to reflect time value of money (TVM) assuming [# years] to exit, execution risk, and macroeconomic uncertainty.<br>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
with st.sidebar.container():
    st.markdown(
        """
        <div style="font-size: 11px; color: #6b6b6b; line-height: 1.35;">
            <b>Disclaimer</b><br><br>
            This tool is provided for indicative purposes only and does not constitute financial or investment advice. Trachet accepts no liability for decisions made in reliance on this tool — founders are strongly advised to seek independent legal, tax, and financial counsel before pursuing any transaction.<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Compute data ----------------------------------------------------------

exit_vals = generate_exit_values(pre_money + raise_goal)

sell_today_vals = compute_sell_today_proceeds(
    exit_vals,
    founders_pct/100,
    historical_pct/100,
    new_pct/100,
    last_post_money,
    liq_pref_bool,
    pref_type,
    pref_multiple,
)

raise_sell_vals = compute_founder_proceeds(
    exit_vals,
    founders_pct/100,
    historical_pct/100,
    new_pct/100,
    pre_money,
    raise_goal,
    show_new_bool,
    liq_pref_bool,
    pref_type,
    pref_multiple,
    last_post_money,
)

risked_vals = apply_risk(raise_sell_vals, risk_pct)

desired = compute_desired_proceeds(exit_vals, sell_today_vals, pre_money)

# difference curve: Raise & Sell proceeds vs desired proceeds (Sell Today at pre_money exit)
# Mirrors Excel AE11 = np.interp(pre_money, exit_vals, sell_today_vals)
difference_vals = raise_sell_vals - desired
difference_vals_risk = risked_vals - desired

# --- Callout values (AF19, AG12, AI10, AG10, BM72) -----------------------
callouts = compute_callout_values(
    exit_vals, raise_sell_vals, founders_pct, pre_money, raise_goal, show_new_bool,
    desired=desired,
)
founders_dil_pct     = callouts["founders_dil_pct"]      # AF19
founders_dilution    = callouts["founders_dilution"]      # AG12
breakeven_sell_today = callouts["breakeven_sell_today"]   # AI10
breakeven_raise_sell = callouts["breakeven_raise_sell"]   # AG10
breakeven_multiple   = callouts["breakeven_multiple"]     # BM72

# --- Output graphs --------------------------------------------------------
st.title("Founder Proceeds by Exit Valuation")

from textwrap import dedent

if breakeven_multiple <= 2.5:
    verdict = "Achievable if your round is structured right."
elif breakeven_multiple <= 3.5:
    verdict = "Stretch territory terms and timing are everything."
else:
    verdict = "Ambitious worth asking if now is the right moment."

# --- Box 3 risk-adjusted variables ---
# Risk-adjusted proceeds at the breakeven exit (i.e. what raise & sell is worth
# in expected value terms, given the founder's own risk estimate)
risk_adjusted_proceeds = desired / (1 + risk_pct)   # desired == sell_today proceeds at pre_money

# The gap: how much worse off the founder is in expected value terms
# even if the raise & sell hits its breakeven exit exactly
risk_gap = desired - risk_adjusted_proceeds          # always positive when risk_pct > 0
# --- Box 3 verdict (risk-adjusted angle) ---
risk_pct_display = int(risk_pct * 100)


verdict = (
        f"At {risk_pct_display}% risk adjusted raise &amp; sell is worth "
         f"<span class='trachet-highlight'>{currency}{round(risk_adjusted_proceeds / 1e6)}m.</span> "
        f"That is <span class='trachet-highlight'>{currency}{round(risk_gap / 1e6)}m</span> "
        f"less than selling today at "
        f"<span class='trachet-highlight'>{currency}{round(desired / 1e6)}m</span>. "
       
    )
callouts_html = dedent(f"""
<div class="trachet-callout-row">
  <div class="trachet-callout">
    <p>
      Your <span class="trachet-highlight">{founders_pct:.1f}%</span> stake
      is worth <span class="trachet-highlight">{currency}{round(desired / 1e6)}m</span>
      today. That's your baseline.
    </p>
  </div>

  <div class="trachet-callout">
    <p>
      A {new_round_name} dilutes you from
      <span class="trachet-highlight">{founders_pct:.1f}%</span> to
      <span class="trachet-highlight">{founders_dil_pct:.1f}%</span>.
      You'll need a <span class="trachet-highlight">{currency}{round(breakeven_raise_sell / 1e6)}m</span>
      ({breakeven_multiple:.1f}x post money {new_round_name}) exit just to match today's value.
    </p>
  </div>

  <div class="trachet-callout">
    <p>{verdict}</p>
  </div>
</div>

""").strip()
#   <div class="trachet-callout">
#     <p>
#       Your breakeven exit multiple is <span class="trachet-highlight">{breakeven_multiple:.1f}x</span>
#       post money {new_round_name}
#       <span class="trachet-highlight">{currency}{round(breakeven_raise_sell / 1e6)}m</span>.
#       {verdict}
#     </p>
#   </div>
  
st.markdown(callouts_html, unsafe_allow_html=True)

st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

#st.markdown("---")

def fmt_parens(v):
    # v is already in "millions" in your chart
    if v < 0:
        return f"({abs(v):,.0f})"
    return f"{v:,.0f}"

# Build nice tick values for y — ~5 ticks, rounded to a clean step
def make_tickvals(data_m, target_ticks=5):
    data_range = data_m.max() - data_m.min()
    raw_step = data_range / (target_ticks - 1)
    # Round step up to nearest nice number (10, 20, 25, 50, 100 …)
    magnitude = 10 ** np.floor(np.log10(raw_step))
    step = magnitude * np.ceil(raw_step / magnitude)
    lo = np.floor(data_m.min() / step) * step
    hi = np.ceil(data_m.max() / step) * step
    return np.arange(lo, hi + step, step)

# y1: cover all four traces shown in fig1
y1_vals = np.concatenate([sell_today_vals, raise_sell_vals, risked_vals, [desired]]) / 1e6
y1_tickvals = make_tickvals(y1_vals)
y1_ticktext = [fmt_parens(x) for x in y1_tickvals]
y1_span = float(y1_tickvals[-1] - y1_tickvals[0]) if len(y1_tickvals) > 1 else 10
y1_range = [y1_tickvals[0] - y1_span * 0.05, y1_tickvals[-1] + y1_span * 0.15]

# y2: difference chart
y2_vals = difference_vals / 1e6
y2_tickvals = make_tickvals(y2_vals)
y2_ticktext = [fmt_parens(x) for x in y2_tickvals]
y2_span = float(y2_tickvals[-1] - y2_tickvals[0]) if len(y2_tickvals) > 1 else 10
y2_range = [y2_tickvals[0] - y2_span * 0.05, y2_tickvals[-1] + y2_span * 0.15]
# ymin_m, ymax_m = -20,60
# dtick=20
# tickvals = np.arange(ymin_m, ymax_m + dtick, dtick) 

x_vals = exit_vals / 1e6

# 5 fixed tick positions across the full x-range
x_tickvals = np.linspace(x_vals.min(), x_vals.max(), 5)
x_tickvals = np.round(x_tickvals / 10) * 10

# Optional: format labels like 50, 100, 150
x_ticktext = [f"{x:,.0f}" for x in x_tickvals]

# chart 1 - Scenario A
fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=sell_today_vals / 1e6,
    mode='lines+markers',
    name='Sell Today',
    line=dict(color=GRAPH_PURPLE, width=2),
    marker=dict(size=5)
))

fig1.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=raise_sell_vals / 1e6,
    mode='lines+markers',
    name='Raise & Sell (R&S)',
    line=dict(color=GRAPH_CYAN, width=2),
    marker=dict(size=5)
))

fig1.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=np.repeat(desired / 1e6, len(exit_vals)),
    mode='lines',
    name='Baseline Proceeds',
    line=dict(color=GRAPH_GREEN, width=2, dash='dash'),
))

fig1.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=risked_vals / 1e6,
    mode='lines+markers',
    name='Risk-Adjusted ⁸',
    line=dict(color=GRAPH_YELLOW, width=1,dash='dot'),
    marker=dict(size=3)
))

import textwrap
disclaimer = "⚠️ Selling in the future is not that straightforward - TVM, Execution & Market risk all work against you."
disclaimer_wrapped = "<br>".join(textwrap.wrap(disclaimer, width=90))
CHART_H = 370


# fig1
fig1.update_layout(
    autosize=True,
    height=CHART_H,
    dragmode="pan",
    xaxis=dict(
        title=f"Exit Valuation ({currency}m)",
        title_font=dict(family=PLOT_FONT, color=PLOT_COLOR),
        tickfont=dict(family=PLOT_FONT, color=PLOT_COLOR),
        # tickformat="(,.0f)",   # e.g. (10) instead of -10
        tickmode="array",
        tickvals=x_tickvals,
        ticktext=x_ticktext,
        #range=[x_vals.min(), x_vals.max()],
    ),
    yaxis=dict(
        title=dict(
            text=f"Founder Proceeds ({currency}m)",
            font=dict(family=PLOT_FONT, color=PLOT_COLOR),
            standoff=19,
        ),
        tickfont=dict(family=PLOT_FONT, color=PLOT_COLOR),
        tickmode="array",
        tickvals=y1_tickvals,
        ticktext=y1_ticktext,
        range=y1_range,
    ),
    plot_bgcolor=PAGE_BG,
    paper_bgcolor=PAGE_BG,
    font=dict(family=PLOT_FONT, color=PLOT_COLOR, size=9),
    hovermode='x unified',
    legend=dict(
        font=dict(color=PLOT_COLOR, size=9),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor=SECONDARY_COLOR,
        borderwidth=1,
        orientation="h",
        x=0.3, xanchor="center",
        y=0.95, yanchor="bottom",
    ),
    margin=dict(t=75, r=20, b=20, l=45)
)
#st.plotly_chart(fig1, use_container_width=True)


# # chart 3 - Scenario C
fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=difference_vals / 1e6,
    mode='lines+markers',
    name='R&S vs Baseline',
    line=dict(color=GRAPH_CYAN, width=2),
    marker=dict(size=5)
))

fig3.add_trace(go.Scatter(
    x=exit_vals / 1e6,
    y=difference_vals_risk / 1e6,
    mode='lines+markers',
    name='R&S vs Risk-Adjusted',
    line=dict(color=GRAPH_YELLOW, width=1,dash='dot'),
    marker=dict(size=3)
))

fig3.add_hline(y=0, line_dash="dash", line_color=SECONDARY_COLOR, #annotation_text="Break-even", 
               #annotation_position="right"
               )

fig3.update_layout(
    autosize=True,
    height=CHART_H,
    dragmode="pan",
    xaxis=dict(
        title=f"Exit Valuation ({currency}m)",
        title_font=dict(family=PLOT_FONT, color=PLOT_COLOR),
        tickfont=dict(family=PLOT_FONT, color=PLOT_COLOR),
        #tickformat="(,.0f)",   # e.g. (10) instead of -10
        tickmode="array",
        tickvals=x_tickvals,
        ticktext=x_ticktext,
        #range=[x_vals.min(), x_vals.max()],
    ),
    yaxis=dict(
        title=dict(
            text=f"Difference ({currency}m)",
            font=dict(family=PLOT_FONT, color=PLOT_COLOR),
            standoff=5,
        ),
        tickfont=dict(family=PLOT_FONT, color=PLOT_COLOR),
        tickmode="array",
        tickvals=y2_tickvals,
        ticktext=y2_ticktext,
        range=y2_range,
    ),
    plot_bgcolor=PAGE_BG,
    paper_bgcolor=PAGE_BG,
    font=dict(family=PLOT_FONT, color=PLOT_COLOR, size=9),
    hovermode='x unified',
    showlegend=True,
    legend=dict(
        font=dict(color=PLOT_COLOR, size=9),
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor=SECONDARY_COLOR,
        borderwidth=1,
        orientation="h",
        x=0.3, xanchor="center",
        y=0.95, yanchor="bottom",
    ),
    margin=dict(t=75, r=20, b=20, l=45),
)
# fig3.update_yaxes(
#     tickmode="array",
#     tickvals=tickvals,
#     ticktext=[fmt_parens(v) for v in tickvals],
# )

#st.plotly_chart(fig3, use_container_width=True)
chart_col1, chart_col2 = st.columns(2, gap="small")

with chart_col1:
    #st.markdown("<p style='font-size:13px;color:rgb(172,176,179);margin-bottom:0;'>Founder Proceeds by Exit Valuation</p>", unsafe_allow_html=True)
    st.plotly_chart(fig1, use_container_width=True,
                    config={
        "displayModeBar": True,   # use "hover" behavior by omitting this, or True to keep it visible
        "displaylogo": False,
        "scrollZoom": False,
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "resetScale2d",
            "hoverCompareCartesian",
            "toggleSpikelines",
            "toImage",
            # "zoomIn2d",
            # "zoomOut2d",
            # "pan2d",
            "zoom2d",
        ],
    },
                    key="fig1")


with chart_col2:
    #st.markdown("<p style='font-size:13px;color:rgb(172,176,179);margin-bottom:0;'>Difference: Raise & Sell vs Baseline by Exit Valuation</p>", unsafe_allow_html=True)
    st.plotly_chart(fig3, use_container_width=True,
                    config={
        "displayModeBar": True,   # use "hover" behavior by omitting this, or True to keep it visible
        "displaylogo": False,
        "scrollZoom": False,
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "resetScale2d",
            "hoverCompareCartesian",
            "toggleSpikelines",
            "toImage",
            # "zoomIn2d",
            # "zoomOut2d",
            # "pan2d",
            "zoom2d",
        ],
    },
                    key="fig3")

st.markdown("<p style='font-size:10px;color:rgb(172,176,179);margin-top:-4px;'>⚠️ Selling in the future is not that straightforward &nbsp;·&nbsp; TVM, Execution &amp; Market risk all work against you.</p>", unsafe_allow_html=True)

import re

st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

# state for showing/hiding the form
if "show_email_form" not in st.session_state:
    st.session_state.show_email_form = False

# Callout-style clickable sentence (button)
if st.button(
    "Want to maximise your exit options? Speak to Trachet before your next Board!",
    type="secondary",
    use_container_width=True,
    key="email_cta_toggle",
):
    st.session_state.show_email_form = not st.session_state.show_email_form

# --- Lead capture helpers ---------------------------------------------------

def _save_lead_csv(data: dict, path: str = "leads.csv"):
    """Append a lead row to leads.csv (persists locally; ephemeral on Streamlit Cloud)."""
    file_exists = os.path.isfile(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def _save_lead_airtable(form: dict, sidebar: dict) -> bool:
    """Create a record in the Airtable 'Form Submissions' table."""
    try:
        from pyairtable import Api
        cfg = st.secrets["airtable"]
        tbl = Api(cfg["api_key"]).table(cfg["base_id"], cfg["table"])
        tbl.create({
            "Name":                   form["Name"],
            "Email":                  form["Email"],
            "Timestamp":              datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "Round name":             sidebar["last_round"],
            "Fundraising goal":       int(sidebar["raise_goal"]),
            "Pre-money valuation":    int(sidebar["pre_money"]),
            "Founders ownership %":   int(sidebar["founders_pct"]),
            "Breakeven multiple":     round(sidebar["breakeven_multiple"], 2),
            "Breakeven exit value":   sidebar["breakeven_raise_sell"],
            "Last round post-money":  sidebar["last_post_money"],
            "Liquidation Preference": sidebar["liq_pref"],
            "Participating?":         sidebar["pref_type"],
            "Cap":                    sidebar["pref_cap"],
            "Founders":               sidebar["founders_pct"] / 100,
            "Historical Investors":   sidebar["historical_pct"] / 100,
            "New Investors":          sidebar["new_pct"] / 100,
        })
        return True
    except Exception as e:
        st.error(f"Airtable save failed: {e}")
        return False


def _send_lead_email(data: dict) -> bool:
    """Send notification email via SMTP using credentials in st.secrets."""
    try:
        cfg = st.secrets["email"]
        sender   = cfg["sender"]
        password = cfg["password"]
        recipient = cfg.get("recipient", "anna@trachet.co")

        msg = MIMEMultipart("alternative")
        msg["From"]    = sender
        msg["To"]      = recipient
        msg["Subject"] = f"New lead — {data.get('Name', 'Unknown')} ({data.get('Company', '')})"

        body_lines = ["New lead from the Founder Proceeds Calculator:\n"]
        for k, v in data.items():
            if v:
                body_lines.append(f"  {k}: {v}")
        body_lines.append(f"\n  Submitted: {data.get('Timestamp', '')}")
        msg.attach(MIMEText("\n".join(body_lines), "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception:
        return False

# --- Reveal the form when toggled on ----------------------------------------
if st.session_state.show_email_form:
    # st.caption("Let's have a call and discuss your results.")

    _PERSONAL_DOMAINS = {
        "gmail.com", "googlemail.com",
        "yahoo.com", "yahoo.co.uk", "yahoo.fr", "yahoo.de", "yahoo.es",
        "yahoo.it", "yahoo.com.au", "yahoo.ca", "yahoo.in",
        "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.de",
        "outlook.com", "outlook.co.uk", "live.com", "live.co.uk", "msn.com",
        "icloud.com", "me.com", "mac.com",
        "aol.com", "aim.com",
        "protonmail.com", "proton.me",
        "zoho.com",
        "mail.com", "email.com", "usa.com",
        "gmx.com", "gmx.net", "gmx.de",
        "yandex.com", "yandex.ru",
        "tutanota.com", "tutamail.com",
        "fastmail.com", "hushmail.com",
        "inbox.com",
    }

    def is_valid_email(addr: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (addr or "").strip()))

    def is_personal_email(addr: str) -> bool:
        domain = (addr or "").strip().lower().split("@")[-1]
        return domain in _PERSONAL_DOMAINS

    with st.form("email_details_form", clear_on_submit=True):
        name = st.text_input("Name *")
        email = st.text_input("Work email *")
        col_a, col_b = st.columns(2)
        with col_a:
            company = st.text_input("Company")
            country = st.text_input("Country")
        with col_b:
            role = st.text_input("Role")
            phone = st.text_input("Phone number")
        consent = st.checkbox("I agree to be contacted by email.")
        submitted = st.form_submit_button("Send me the details", type="primary")

    if submitted:
        if not consent:
            st.error("Please confirm consent to be contacted.")
        elif not name.strip():
            st.error("Please enter your name.")
        elif not is_valid_email(email):
            st.error("Please enter a valid email address.")
        elif is_personal_email(email):
            st.warning("Please use your work email address. Personal email providers (Gmail, Yahoo, Outlook, etc.) are not accepted.")
        else:
            lead = {
                "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "Name": name.strip(),
                "Email": email.strip(),
                "Company": company.strip(),
                "Role": role.strip(),
                "Country": country.strip(),
                "Phone": phone.strip(),
            }
            _save_lead_csv(lead)
            _save_lead_airtable(lead, {
                "last_round":          last_round,
                "raise_goal":          raise_goal,
                "pre_money":           pre_money,
                "founders_pct":        founders_pct,
                "historical_pct":      historical_pct,
                "new_pct":             new_pct,
                "last_post_money":     last_post_money,
                "liq_pref":            liq_pref,
                "pref_type":           pref_type,
                "pref_cap":            pref_cap,
                "breakeven_multiple":  breakeven_multiple,
                "breakeven_raise_sell": breakeven_raise_sell,
            })
            email_ok = _send_lead_email(lead)
            if email_ok:
                st.success("Thanks — we’ll be in touch shortly.")
            else:
                st.success("Thanks — your details have been saved.")

# display raw data table for debugging
# with st.expander("Show detailed data"):
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.subheader("Scenario A")
#         chart1_df = pd.DataFrame({
#             "Exit Valuation (M)": exit_vals / 1e6,
#             "Sell Today (M)": sell_today_vals / 1e6,
#             "Raise & Sell (M)": raise_sell_vals / 1e6,
#             "Desired (M)": np.repeat(desired / 1e6, len(exit_vals)),
#         })
#         st.dataframe(chart1_df, use_container_width=True)
#     with col2:
#         st.subheader("Scenario B")
#         chart2_df = pd.DataFrame({
#             "Exit Valuation (M)": exit_vals / 1e6,
#             "Raise & Sell (M)": raise_sell_vals / 1e6,
#             "Risk-Adjusted (M)": risked_vals / 1e6,
#             "Desired (M)": np.repeat(desired / 1e6, len(exit_vals)),
#         })
#         st.dataframe(chart2_df, use_container_width=True)
#     with col3:
#         st.subheader("Scenario C")
#         chart3_df = pd.DataFrame({
#             "Exit Valuation (M)": exit_vals / 1e6,
#             "Difference (M)": difference_vals / 1e6,
#         })
#         st.dataframe(chart3_df, use_container_width=True)

  
