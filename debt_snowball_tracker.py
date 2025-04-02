import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import json
from pathlib import Path
from fpdf import FPDF

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

# Initialize session state
if "num_accounts" not in st.session_state:
    st.session_state.num_accounts = 3
if "num_extra" not in st.session_state:
    st.session_state.num_extra = 0
if "remove_index" not in st.session_state:
    st.session_state.remove_index = None
if "remove_extra_index" not in st.session_state:
    st.session_state.remove_extra_index = None

st.title("Debt Snowball Tracker")
SAVE_PATH = Path("debt_inputs.json")

def load_inputs():
    if SAVE_PATH.exists():
        return json.loads(SAVE_PATH.read_text())
    return {
        "accounts": [
            {"name": "Citi", "balance": 5174.0, "apr": 11.99, "payment": 290.0},
            {"name": "Discover 0434", "balance": 5057.0, "apr": 11.99, "payment": 164.0},
            {"name": "Discover 1258", "balance": 5431.0, "apr": 11.99, "payment": 166.0},
        ],
        "extra_payment": 0.0,
        "monthly_income": 0.0,
        "extras": []
    }

def save_inputs(data):
    SAVE_PATH.write_text(json.dumps(data))

inputs = load_inputs()

# Adjust number of accounts
if len(inputs["accounts"]) > st.session_state.num_accounts:
    st.session_state.num_accounts = len(inputs["accounts"])
if len(inputs.get("extras", [])) > st.session_state.num_extra:
    st.session_state.num_extra = len(inputs["extras"])

if st.button("Add Another Account"):
    st.session_state.num_accounts += 1
if st.button("Add Scheduled Extra Payment"):
    st.session_state.num_extra += 1

accounts = inputs.get("accounts", [])
extra_payment = inputs.get("extra_payment", 0.0)
monthly_income = inputs.get("monthly_income", 0.0)
extra_schedule = inputs.get("extras", [])

with st.form("debt_form"):
    updated_accounts = []
    st.markdown("### Debt Accounts")
    for i in range(st.session_state.num_accounts):
        default = accounts[i] if i < len(accounts) else {"name": f"Card {i+1}", "balance": 0.0, "apr": 0.0, "payment": 0.0}
        with st.expander(f"{default['name']} (Click to Edit)"):
            cols = st.columns([3, 2, 2, 2, 1])
            name = cols[0].text_input(f"Name {i+1}", value=default["name"], key=f"name_{i}")
            balance = cols[1].number_input(f"Balance {i+1}", value=default["balance"], step=100.0, min_value=0.0, key=f"balance_{i}")
            apr = cols[2].number_input(f"APR (%) {i+1}", value=default["apr"], step=0.1, min_value=0.0, key=f"apr_{i}")
            payment = cols[3].number_input(f"Payment {i+1}", value=default["payment"], step=10.0, min_value=0.0, key=f"payment_{i}")
            delete = cols[4].checkbox("Delete", key=f"delete_{i}")
            if delete:
                st.session_state.remove_index = i
            else:
                updated_accounts.append({"name": name, "balance": balance, "apr": apr, "payment": payment})

    st.markdown("### Scheduled Extra Payments")
    updated_extras = []
    for i in range(st.session_state.num_extra):
        default = extra_schedule[i] if i < len(extra_schedule) else {"amount": 0.0, "start_month": 0}
        col1, col2, col3 = st.columns([4, 4, 1])
        amount = col1.number_input(f"Extra Amount {i+1}", value=default["amount"], step=10.0, min_value=0.0, key=f"extra_amt_{i}")
        start_month = col2.number_input(f"Start Month {i+1}", value=default["start_month"], step=1, min_value=0, key=f"start_month_{i}")
        delete = col3.checkbox("Delete", key=f"delete_extra_{i}")
        if delete:
            st.session_state.remove_extra_index = i
        else:
            updated_extras.append({"amount": amount, "start_month": start_month})

    extra_payment = st.number_input("Extra Monthly Payment", min_value=0.0, value=extra_payment, step=10.0)
    monthly_income = st.number_input("Monthly Income (optional)", min_value=0.0, value=monthly_income, step=100.0)
    submitted = st.form_submit_button("Calculate Payoff", type="primary")

if st.session_state.remove_index is not None:
    st.session_state.num_accounts -= 1
    st.session_state.remove_index = None
    st.experimental_rerun()

if st.session_state.remove_extra_index is not None:
    st.session_state.num_extra -= 1
    st.session_state.remove_extra_index = None
    st.experimental_rerun()

if submitted:
    save_inputs({"accounts": updated_accounts, "extra_payment": extra_payment, "monthly_income": monthly_income, "extras": updated_extras})
    debts = sorted(updated_accounts, key=lambda x: x["balance"])
    month = 0
    history = []
    initial_debt = sum(d["balance"] for d in debts)

    while any(debt["balance"] > 0 for debt in debts):
        total_payment = sum(d["payment"] for d in debts if d["balance"] > 0)
        snowball_extra = extra_payment + sum(e["amount"] for e in updated_extras if e["start_month"] <= month)
        total_balance = sum(d["balance"] for d in debts)
        history.append({"Month": month, "Total Debt": total_balance, "Progress": 1 - total_balance / initial_debt})

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
    if monthly_income:
        dti = initial_debt / monthly_income
        st.info(f"Debt-to-Income Ratio: {dti:.2f} (Based on total starting debt and monthly income)")

    df = pd.DataFrame(history)
    st.progress(df.iloc[-1]["Progress"] if not df.empty else 0.0)

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
    st.pyplot(fig)

    csv = df.to_csv(index=False)
    st.download_button("Download Payoff Timeline as CSV", data=csv, file_name="debt_snowball_payoff_timeline.csv", mime="text/csv")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Debt Snowball Payoff Report", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Total Months to Payoff: {month} (~{month//12} years, {month%12} months)", ln=2)
    pdf.cell(200, 10, txt="Month-by-Month Debt Reduction:", ln=3)
    for row in history:
        pdf.cell(200, 8, txt=f"Month {int(row['Month'])}: ${row['Total Debt']:.2f}", ln=1)

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    st.download_button("Download Payoff Report as PDF", data=pdf_buffer.getvalue(), file_name="debt_payoff_report.pdf", mime="application/pdf")
