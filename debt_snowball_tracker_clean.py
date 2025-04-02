
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

# Utility functions
def render_chart(df, label=None):
    fig, ax = plt.subplots()
    if label:
        ax.plot(df["Month"], df["Total Debt"], marker="o", label=label)
    else:
        ax.plot(df["Month"], df["Total Debt"], marker="o")
    ax.axhline(0, color='gray', linestyle='--')
    for m in [12, 24, 36, 48, 60]:
        ax.axvline(m, color='green', linestyle=':', alpha=0.3)
        ax.text(m, ax.get_ylim()[1]*0.95, f"{m} mo", rotation=90, color='green')
    ax.set_title("Debt Payoff Progress")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Debt ($)")
    ax.grid(True)
    if label:
        ax.legend()
    return fig

# Placeholder content (replace with your real logic from canvas)
st.title("Debt Snowball Tracker")

st.write("This is a placeholder version of the app with no state-saving logic.")
st.write("To use the full version, copy in the final logic from your canvas document.")
