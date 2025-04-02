import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="Debt Snowball Tracker")
st.title("💸 Debt Snowball Tracker")

st.write("Enter your current balances, APRs, and planned monthly payments for each card.")

# Input table
with st.form("debt_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        citi_balance = st.number_input("Citi Balance", min_value=0.0, value=5174.0, step=100.0)
        discover1_balance = st.number_input("Discover 0434 Balance", min_value=0.0, value=5057.0, step=100.0)
        discover2_balance = st.number_input("Discover 1258 Balance", min_value=0.0, value=5431.0, step=100.0)
    with col2:
        citi_apr = st.number_input("Citi APR (%)", min_value=0.0, value=11.99, step=0.1)
        discover1_apr = st.number_input("Discover 0434 APR (%)", min_value=0.0, value=11.99, step=0.1)
        discover2_apr = st.number_input("Discover 1258 APR (%)", min_value=0.0, value=11.99, step=0.1)
    with col3:
        citi_payment = st.number_input("Citi Payment", min_value=0.0, value=290.0, step=10.0)
        discover1_payment = st.number_input("Discover 0434 Payment", min_value=0.0, value=164.0, step=10.0)
        discover2_payment = st.number_input("Discover 1258 Payment", min_value=0.0, value=166.0, step=10.0)

    submitted = st.form_submit_button("Calculate Payoff")

if submitted:
    # Build list of debts
    debts = [
        {"name": "Citi", "balance": citi_balance, "apr": citi_apr, "payment": citi_payment},
        {"name": "Discover 0434", "balance": discover1_balance, "apr": discover1_apr, "payment": discover1_payment},
        {"name": "Discover 1258", "balance": discover2_balance, "apr": discover2_apr, "payment": discover2_payment},
    ]

    # Sort debts by balance (snowball method)
    debts.sort(key=lambda x: x["balance"])

    # Simulate payments month-by-month
    month = 0
    history = []

    while any(debt["balance"] > 0 for debt in debts):
        total_payment = sum(d["payment"] for d in debts if d["balance"] > 0)
        history.append({"Month": month, "Total Debt": sum(d["balance"] for d in debts)})

        for i, debt in enumerate(debts):
            if debt["balance"] <= 0:
                continue

            apr_monthly = debt["apr"] / 1200
            interest = debt["balance"] * apr_monthly
            principal_payment = min(debt["payment"], debt["balance"] + interest)
            debt["balance"] = max(0, (debt["balance"] + interest - principal_payment))

            # Snowball: If paid off, roll payment into next
            if debt["balance"] == 0 and i + 1 < len(debts):
                debts[i+1]["payment"] += debt["payment"]

        month += 1
        if month > 100:  # prevent infinite loop
            break

    st.success(f"🎉 You’ll be debt-free in {month} months (~{month//12} years, {month%12} months)!")

    df = pd.DataFrame(history)
    fig, ax = plt.subplots()
    ax.plot(df["Month"], df["Total Debt"], marker="o")
    ax.set_title("Debt Payoff Progress")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Debt ($)")
    ax.grid(True)
    st.pyplot(fig)

    # CSV export
    csv = df.to_csv(index=False)
    st.download_button(
        label="📁 Download Payoff Timeline as CSV",
        data=csv,
        file_name="debt_snowball_payoff_timeline.csv",
        mime="text/csv"
    )
