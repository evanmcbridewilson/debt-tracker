import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import base64
import tempfile
import calendar
import datetime

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

# ---------- Utility Functions ----------

def render_chart(df):
    fig, ax = plt.subplots()
    ax.plot(df["Month"], df["Total Debt"], marker="o")
    ax.axhline(0, color='gray', linestyle='--')
    
    ax.set_title("Debt Payoff Progress")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Debt ($)")
    ax.grid(True)
    return fig

def generate_pdf(history, month, chart_path, final_date):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Debt Snowball Payoff Report", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Total Months to Payoff: {month} (~{month//12} years, {month%12} months) — by {final_date.strftime('%B %Y')}", ln=2)
    pdf.ln(5)
    pdf.image(chart_path, x=10, y=30, w=180)
    pdf.ln(100)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Month-by-Month Debt Reduction (starting from {final_date.strftime('%B %Y')}):", ln=1)
    for row in history:
        pdf.cell(200, 8, txt=f"Month {int(row['Month'])}: ${row['Total Debt']:.2f}", ln=1)
    return pdf.output(dest='S').encode('latin-1', errors='ignore')

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
        acc["name"] = cols[0].text_input("Name", value=acc["name"], placeholder="e.g. Credit Card", key=f"name_{i}")
        acc["balance"] = cols[1].number_input("Balance", value=None if acc["balance"] == 0.0 else acc["balance"], step=100.0, min_value=0.0, placeholder="e.g. 2500.00", key=f"balance_{i}")
        acc["apr"] = cols[2].number_input("APR (%)", value=None if acc["apr"] == 0.0 else acc["apr"], step=0.1, min_value=0.0, placeholder="e.g. 19.99", key=f"apr_{i}")
        acc["payment"] = cols[3].number_input("Monthly Payment", value=None if acc["payment"] == 0.0 else acc["payment"], step=10.0, min_value=0.0, placeholder="e.g. 100.00", key=f"payment_{i}")
        if cols[4].button("🗑️", key=f"delete_{i}"):
            delete_indices.append(i)

for i in sorted(delete_indices, reverse=True):
    del st.session_state.accounts[i]
    st.experimental_rerun()

if st.button("➕ Add Account"):
    st.session_state.accounts.append({"name": "", "balance": 0.0, "apr": 0.0, "payment": 0.0})
    st.experimental_rerun()

st.markdown("### Additional Monthly Payment")
extra_payment = st.number_input("Extra Monthly Payment", min_value=0.0, value=None, step=10.0, placeholder="e.g. 200.00", format="%.2f")

st.markdown("### Scheduled Extra Payments")
delete_extra = []
for i, ex in enumerate(st.session_state.extras):
    col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
    ex["amount"] = col1.number_input(f"Amount {i+1}", value=None if ex["amount"] == 0.0 else ex["amount"], step=10.0, min_value=0.0, placeholder="e.g. 500.00", key=f"extra_amt_{i}")
    month_names = [calendar.month_name[m] for m in range(1, 13)]
    ex_month = col2.selectbox(f"Start Month", options=month_names, index=(ex.get("month", 1) - 1), key=f"extra_month_{i}")
    ex_year = col3.number_input("Year", min_value=datetime.datetime.now().year, value=ex.get("year", datetime.datetime.now().year), step=1, key=f"extra_year_{i}")
    ex["month"] = month_names.index(ex_month) + 1
    ex["year"] = ex_year
    if col4.button("🗑️", key=f"delete_extra_{i}"):
        delete_extra.append(i)

for i in sorted(delete_extra, reverse=True):
    del st.session_state.extras[i]
    st.experimental_rerun()

if st.button("➕ Add Scheduled Extra Payment"):
    st.session_state.extras.append({"amount": 0.0, "month": 1, "year": datetime.datetime.now().year})
    st.experimental_rerun()

if st.button("Calculate Payoff"):
    debts = sorted(st.session_state.accounts, key=lambda x: x["balance"])
    extras = st.session_state.extras
    month = 0
    history = []
    initial_debt = sum(d["balance"] for d in debts)
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month

    while any(d["balance"] > 0 for d in debts):
        sim_month = (current_month + month - 1) % 12 + 1
        sim_year = current_year + (current_month + month - 1) // 12
        snowball_extra = (extra_payment or 0.0) + sum(
            e["amount"] for e in extras
            if (e["year"] < sim_year) or (e["year"] == sim_year and e["month"] <= sim_month)
        ) or (e["year"] == sim_year and e["month"] <= sim_month))
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

    final_date = datetime.date(current_year, current_month, 1) + pd.DateOffset(months=month)
    st.success(f"You’ll be debt-free in {month} months (~{month//12} years, {month%12} months) — by {final_date.strftime('%B %Y')}!")
    df = pd.DataFrame(history)
    df["Date"] = [
        (datetime.date(current_year, current_month, 1) + pd.DateOffset(months=i)).strftime("%B %Y")
        for i in df["Month"]
    ]
    chart = render_chart(df)
    st.pyplot(chart)

    
    st.markdown(f"### Month-by-Month Debt Reduction (starting from {datetime.date.today().strftime('%B %Y')}):")
st.dataframe(df[["Date", "Total Debt"]].style.format({"Total Debt": "${:,.2f}"}))
