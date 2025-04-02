
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

# -- Utility Functions --

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

def generate_pdf(history, month):
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
    return pdf_buffer.getvalue()

# -- App Start --

st.title("Debt Snowball Tracker")

with st.form("debt_form"):
    st.markdown("### Debt Accounts")
    num_accounts = st.number_input("Number of Accounts", min_value=1, max_value=10, value=3, step=1)
    accounts = []
    for i in range(int(num_accounts)):
        st.subheader(f"Account {i+1}")
        name = st.text_input(f"Name {i+1}", key=f"name_{i}")
        balance = st.number_input(f"Balance {i+1}", min_value=0.0, key=f"balance_{i}")
        apr = st.number_input(f"APR (%) {i+1}", min_value=0.0, key=f"apr_{i}")
        payment = st.number_input(f"Monthly Payment {i+1}", min_value=0.0, key=f"payment_{i}")
        accounts.append({ "name": name, "balance": balance, "apr": apr, "payment": payment })

    extra_payment = st.number_input("Extra Monthly Payment", min_value=0.0, step=10.0)
    submitted = st.form_submit_button("Calculate Payoff")

if submitted:
    debts = sorted(accounts, key=lambda x: x["balance"])
    history = []
    month = 0
    initial_debt = sum(d["balance"] for d in debts)

    while any(d["balance"] > 0 for d in debts):
        snowball_extra = extra_payment
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
    st.pyplot(render_chart(df))
    csv = df.to_csv(index=False)
    st.download_button("Download Payoff Timeline as CSV", data=csv, file_name="debt_snowball_payoff_timeline.csv", mime="text/csv")
    st.download_button("Download Payoff Report as PDF", data=generate_pdf(history, month), file_name="debt_payoff_report.pdf", mime="application/pdf")
