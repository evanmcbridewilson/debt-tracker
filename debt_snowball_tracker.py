import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import json
from pathlib import Path
from fpdf import FPDF

st.set_page_config(page_title="Debt Snowball Tracker", layout="wide")

SAVE_PATH = Path("debt_inputs.json")

# Utility functions

def load_inputs():
    if SAVE_PATH.exists():
        return json.loads(SAVE_PATH.read_text())
    return {"accounts": [], "extra_payment": None, "monthly_income": None, "extras": [], "scenarios": {}}

def save_inputs(data):
    SAVE_PATH.write_text(json.dumps(data))

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

def generate_multi_scenario_pdf(scenarios):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Multi-Scenario Debt Snowball Comparison", ln=1, align="C")
    pdf.ln(10)
    for name, data in scenarios.items():
        df = pd.DataFrame(data)
        final_month = df["Month"].iloc[-1]
        pdf.cell(200, 8, txt=f"{name}: {final_month} months (~{final_month//12} yrs, {final_month%12} mo)", ln=1)
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

# -- (form code remains unchanged) --

    if scenario_name:
        inputs["scenarios"][scenario_name] = df.to_dict(orient="list")
        save_inputs(inputs)

    st.progress(df.iloc[-1]["Progress"] if not df.empty else 0.0)
    st.pyplot(render_chart(df))

    # -- Scenario comparison charts
    if len(inputs["scenarios"]) > 1:
        st.markdown("## 📊 Compare Saved Scenarios")
        selected = st.multiselect("Select scenarios to compare:", options=list(inputs["scenarios"].keys()))

        if selected:
            fig, ax = plt.subplots()
            table_data = []
            for name in selected:
                sdf = pd.DataFrame(inputs["scenarios"][name])
                ax.plot(sdf["Month"], sdf["Total Debt"], label=name)
                payoff_month = sdf["Month"].iloc[-1]
                table_data.append({"Scenario": name, "Months to Payoff": payoff_month, "Years": payoff_month//12, "Months": payoff_month%12})
            ax.set_title("Scenario Comparison")
            ax.set_xlabel("Month")
            ax.set_ylabel("Total Debt ($)")
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)

            st.markdown("### Summary Table")
            st.dataframe(pd.DataFrame(table_data))

            pdf_multi = generate_multi_scenario_pdf({name: inputs["scenarios"][name] for name in selected})
            st.download_button("Download Multi-Scenario PDF", data=pdf_multi, file_name="multi_scenario_comparison.pdf", mime="application/pdf")

    # -- Delete scenario logic
    if inputs["scenarios"]:
        st.markdown("## 🗑️ Delete Saved Scenario")
        delete_choice = st.selectbox("Select scenario to delete:", list(inputs["scenarios"].keys()))
        if st.button("Delete Selected Scenario"):
            del inputs["scenarios"][delete_choice]
            save_inputs(inputs)
            st.success(f"Scenario '{delete_choice}' deleted. Please refresh or reselect options.")

    # -- Export options
    csv = df.to_csv(index=False)
    st.download_button("Download Payoff Timeline as CSV", data=csv, file_name="debt_snowball_payoff_timeline.csv", mime="text/csv")
    st.download_button("Download Payoff Report as PDF", data=generate_pdf(history, month), file_name="debt_payoff_report.pdf", mime="application/pdf")
