from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

# ─────────────────────── PATHS ───────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    "clients": DATA_DIR / "clients.csv",
    "projects": DATA_DIR / "projects.csv",
    "salaries": DATA_DIR / "salaries.csv",
    "expenses": DATA_DIR / "expenses.csv",
    "monthly": DATA_DIR / "monthly.csv",
}

COLUMNS = {
    "clients":  ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "monthly":  ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"]
}

for k, p in FILES.items():
    if not p.exists():
        pd.DataFrame(columns=COLUMNS[k]).to_csv(p, index=False)

clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
monthly_df  = pd.read_csv(FILES["monthly"])

st.set_page_config("33Studio Dashboard", layout="wide")
st.title("📊 33Studio — Finance Dashboard")

page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Invoice Generator", "Analytics", "Monthly Plans"
])

def save_df(df, csv): df.to_csv(csv, index=False)
def money(x): return f"${x:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "33Studio — Payment Request", ln=True, align="C")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    def monthly_invoice(self, row):
        self.set_font("Helvetica", size=11)
        self.cell(0, 10, f"Payment Request for {row['Client']}", ln=True)
        self.cell(0, 10, f"Amount Due: ${row['Amount']:.2f}", ln=True)
        self.cell(0, 10, f"Payment Method: {row['Payment Method']}", ln=True)
        self.cell(0, 10, f"Due Date: 28 {row['Month']}", ln=True)
        self.ln(5)
        self.cell(0, 10, "Please make the payment by the due date.", ln=True)

# ─────────────────────── PAGES ───────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    clients_df[["Total Paid", "Total Due"]] = clients_df[["Total Paid", "Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    total_income = clients_df["Total Paid"].sum()
    total_due = clients_df["Total Due"].sum()
    paid_salaries = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_salaries = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_expenses = expenses_df["Amount"].sum() + paid_salaries

    for c, (label, val) in zip(st.columns(5), [
        ("Income", total_income),
        ("Outstanding", total_due),
        ("Expenses", total_expenses),
        ("Paid Salaries", paid_salaries),
        ("Unpaid Salaries", unpaid_salaries)
    ]): c.metric(label, money(val))

elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    st.subheader("Clients")
    clients_df = st.data_editor(clients_df, num_rows='dynamic', use_container_width=True, key='edit_clients')
    if st.button("💾 Save Clients"): save_df(clients_df, FILES["clients"])

    st.divider()
    st.subheader("Projects")
    projects_df = st.data_editor(projects_df, num_rows='dynamic', use_container_width=True, key='edit_projects')
    if st.button("💾 Save Projects"): save_df(projects_df, FILES["projects"])

elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    salaries_df = st.data_editor(salaries_df, num_rows='dynamic', use_container_width=True, key='edit_salaries')
    if st.button("💾 Save Salaries"): save_df(salaries_df, FILES["salaries"])

elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    expenses_df = st.data_editor(expenses_df, num_rows='dynamic', use_container_width=True, key='edit_expenses')
    if st.button("💾 Save Expenses"): save_df(expenses_df, FILES["expenses"])

elif page == "Analytics":
    st.header("📊 Financial Charts")
    try:
        fig = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
        st.plotly_chart(fig, use_container_width=True)
    except: st.warning("Missing data for client income chart.")

    try:
        projects_df["Budget"] = pd.to_numeric(projects_df["Budget"], errors="coerce").fillna(0)
        milestone_sum = {
            "20%": projects_df["Payment 20%"].sum(),
            "40%": projects_df["Payment 40%"].sum(),
            "40% (2)": projects_df["Payment 40% (2)"].sum(),
        }
        fig2 = px.pie(values=list(milestone_sum.values()), names=list(milestone_sum.keys()), hole=0.4, title="Project Payment Distribution")
        st.plotly_chart(fig2, use_container_width=True)
    except: st.warning("Missing data for milestone pie chart.")

    try:
        exp_sum = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(exp_sum, values="Amount", names="Category", title="Expense Breakdown", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
    except: st.warning("Missing data for expense pie chart.")

elif page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.info("No projects available.")
    else:
        client = st.selectbox("Client", projects_df["Client"].unique())
        filtered = projects_df[projects_df["Client"] == client]
        project = st.selectbox("Project", filtered["Project"].unique())
        selected = filtered[filtered["Project"] == project].iloc[0]
        milestone_label, amount = None, 0
        for m in ["Payment 20%", "Payment 40%", "Payment 40% (2)"]:
            if pd.notnull(selected[m]) and selected[m] > 0:
                milestone_label = m; amount = selected[m]
                break
        if milestone_label:
            st.write(f"Next payment due: **{milestone_label}** — ${amount:,.2f}")
            if st.button("Generate Invoice PDF"):
                pdf = InvoicePDF(); pdf.add_page()
                pdf.set_font("Helvetica", size=12)
                for field in ["Client", "Project", "Employee"]:
                    pdf.cell(0, 10, f"{field}: {selected[field]}", ln=True)
                pdf.cell(0, 10, f"{milestone_label}: ${amount:,.2f}", ln=True)
                filename = f"Invoice_{client.replace(' ', '_')}_{milestone_label.replace('%', '')}.pdf"
                path = INV_DIR / filename
                pdf.output(str(path))
                st.download_button("📥 Download PDF", open(path, "rb"), file_name=filename)
        else:
            st.success("All milestones are paid.")

elif page == "Monthly Plans":
    st.header("📅 Monthly Payment Plans")
    st.subheader("New Plan")
    with st.form("add_monthly", clear_on_submit=True):
        client = st.selectbox("Client", clients_df["Client"].unique())
        amount = st.number_input("Amount", 0.0)
        method = st.selectbox("Method", ["Fast Pay", "Zain Cash", "FIB", "Money Transfer", "Bank Transfer"])
        sm_budget = st.checkbox("Includes Social Media Budget")
        paid = st.selectbox("Paid?", ["No", "Yes"])
        if st.form_submit_button("Save Plan"):
            monthly_df.loc[len(monthly_df)] = {
                "Client": client, "Amount": amount, "Payment Method": method,
                "Social Media Budget": "Yes" if sm_budget else "No",
                "Paid": paid, "Month": date.today().strftime("%B %Y")
            }
            save_df(monthly_df, FILES["monthly"])
            st.rerun()

    st.subheader("📋 This Month")
    st.dataframe(monthly_df[monthly_df["Month"] == date.today().strftime("%B %Y")])

    st.subheader("🚨 Unpaid Clients")
    unpaid = monthly_df[(monthly_df["Paid"] == "No") & (monthly_df["Month"] == date.today().strftime("%B %Y"))]
    for i, row in unpaid.iterrows():
        with st.expander(f"{row['Client']} — ${row['Amount']:.2f}"):
            if st.button(f"📄 Generate Payment Request — {row['Client']}", key=f"inv_{i}"):
                try:
                    pdf = InvoicePDF(); pdf.add_page(); pdf.monthly_invoice(row)
                    fname = f"MonthlyInvoice_{row['Client'].replace(' ', '_')}_{row['Month'].replace(' ', '_')}.pdf"
                    path = INV_DIR / fname
                    pdf.output(str(path))
                    st.download_button("📥 Download PDF", open(path, "rb"), file_name=fname)
                    st.success("PDF Created")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

    st.subheader("✏️ Edit Monthly Plans")
    monthly_df = st.data_editor(monthly_df, num_rows="dynamic", use_container_width=True, key="edit_monthly")
    if st.button("💾 Save Monthly Plans"):
        save_df(monthly_df, FILES["monthly"])
        st.success("Saved")
