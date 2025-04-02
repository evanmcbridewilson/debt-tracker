import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import base64
import tempfile

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

# ---------- Utility Functions ----------

def render_chart(df):
    fig, ax = plt.subplots()
    ax.plot(df["Month"], df["Total Debt"], marker="o")
    ax.axhline(0, color='gray', linestyle='--')
    for m in [12, 24, 36, 48, 60]:
        ax.axvline(m, color='green', linestyle=':', alpha=0.3)
        ax.text(m, ax.get_ylim()[1]*0.95, f"{m} mo", rotation=90, color='green')
    ax.set_title("Debt Payoff Progress")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Debt ($)")
    ax.grid(True)
    return fig

def generate_pdf(history, month, chart_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Debt Snowball Payoff Report", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Total Months to Payoff: {month} (~{month//12} years, {month%12} months)", ln=2)
    pdf.ln(5)
    pdf.image(chart_path, x=10, y=30, w=180)
    pdf.ln(100)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Month-by-Month Debt Reduction:", ln=1)
    for row in history:
        pdf.cell(200, 8, txt=f"Month {int(row['Month'])}: ${row['Total Debt']:.2f}", ln=1)
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

# ---------- App UI ----------

st.title("Debt Snowball Tracker")

if "accounts" not in st.session_state:
    st.session_state.accounts = [{"name": "", "balance": 0.0, "apr": 0.0, "payment": 0.0}]
if "extras" not in st.session_state:
    st.session_state.extras = []

st.markdown("### Debt Accounts")

delete_indices = []
for i, acc in enumerate(st.session_state.accounts):
    with st.expander(f"Account {i+1}"):
        cols = st.columns([3, 2, 2, 2, 1])
        acc["name"] = cols[0].text_input("Name", value=acc["name"], key=f"name_{i}")
        acc["balance"] = cols[1].number_input("Balance", value=acc["balance"], step=100.0, min_value=0.0, key=f"balance_{i}")
        acc["apr"] = cols[2].number_input("APR (%)", value=acc["apr"], step=0.1, min_value=0.0, key=f"apr_{i}")
        acc["payment"] = cols[3].number_input("Monthly Payment", value=acc["payment"], step=10.0, min_value=0.0, key=f"payment_{i}")
        if cols[4].button("🗑️", key=f"delete_{i}"):
            delete_indices.append(i)

for i in sorted(delete_indices, reverse=True):
    del st.session_state.accounts[i]

if st.button("➕ Add Account"):
    st.session_state.accounts.append({"name": "", "balance": 0.0, "apr": 0.0, "payment": 0.0})

st.markdown("### Additional Monthly Payment")
extra_payment = st.number_input("Extra Monthly Payment", min_value=0.0, value=0.0, step=10.0, format="%.2f")

st.markdown("### Scheduled Extra Payments")
delete_extra = []
for i, ex in enumerate(st.session_state.extras):
    col1, col2, col3 = st.columns([4, 4, 1])
    ex["amount"] = col1.number_input(f"Amount {i+1}", value=ex["amount"], step=10.0, min_value=0.0, key=f"extra_amt_{i}")
    ex["start_month"] = col2.number_input(f"Start Month {i+1}", value=ex["start_month"], step=1, min_value=0, key=f"start_month_{i}")
    if col3.button("🗑️", key=f"delete_extra_{i}"):
        delete_extra.append(i)

for i in sorted(delete_extra, reverse=True):
    del st.session_state.extras[i]

if st.button("➕ Add Scheduled Extra Payment"):
    st.session_state.extras.append({"amount": 0.0, "start_month": 0})

if st.button("Calculate Payoff"):
    debts = sorted(st.session_state.accounts, key=lambda x: x["balance"])
    extras = st.session_state.extras
    month = 0
    history = []
    initial_debt = sum(d["balance"] for d in debts)

    while any(d["balance"] > 0 for d in debts):
        snowball_extra = extra_payment + sum(e["amount"] for e in extras if e["start_month"] <= month)
        total_balance = sum(d["balance"] for d in debts)
        history.append({"Month": month, "Total Debt": total_balance})

        for i, debt in enumerate(debts):
            if debt["balance"] <= 0:
                continue
            apr_monthly = debt["apr"] / 1200
            interest = debt["balance"] * apr_monthly
            principal_payment = min(debt["payment"] + snowball_extra, debt["balance"] + interest)
            snowball_extra = max(0, snowball_extra - max(0, principal_payment - debt["payment"]))
            debt["balance"] = max(0, (debt["balance"] + interest - principal_payment))
            if debt["balance"] == 0 and i + 1 < len(debts):
                debts[i+1]["payment"] += debt["payment"]

        month += 1
        if month > 300:
            break

    st.success(f"You’ll be debt-free in {month} months (~{month//12} years, {month%12} months)!")
    df = pd.DataFrame(history)
    chart = render_chart(df)
    st.pyplot(chart)

    csv = df.to_csv(index=False)
    st.download_button("Download Payoff Timeline as CSV", data=csv, file_name="debt_snowball_payoff_timeline.csv", mime="text/csv")

    # Save chart to temp file for PDF
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        chart.savefig(tmpfile.name, bbox_inches='tight')
        chart_path = tmpfile.name

    pdf_bytes = generate_pdf(history, month, chart_path)
    st.download_button("Download Payoff Report as PDF", data=pdf_bytes, file_name="debt_payoff_report.pdf", mime="application/pdf")
