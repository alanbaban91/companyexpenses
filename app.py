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
INV_DIR = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    "clients": DATA_DIR / "clients.csv",
    "projects": DATA_DIR / "projects.csv",
    "salaries": DATA_DIR / "salaries.csv",
    "expenses": DATA_DIR / "expenses.csv",
    "monthly": DATA_DIR / "monthly.csv",
}

COLUMNS = {
    "clients": ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "monthly": ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"]
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

# ─────────────────────── DASHBOARD ───────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    clients_df[["Total Paid", "Total Due"]] = clients_df[["Total Paid", "Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    total_income   = clients_df["Total Paid"].sum()
    total_due      = clients_df["Total Due"].sum()
    paid_salaries  = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_salaries= salaries_df.query("Paid=='No'")["Salary"].sum()
    total_expenses = expenses_df["Amount"].sum() + paid_salaries

    for c, (label, val) in zip(st.columns(5), [
        ("Income", total_income),
        ("Outstanding", total_due),
        ("Expenses", total_expenses),
        ("Paid Salaries", paid_salaries),
        ("Unpaid Salaries", unpaid_salaries)
    ]): c.metric(label, money(val))

# ─────────────────────── CLIENTS & PROJECTS ───────────────────────
elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")

    with st.form("add_client", clear_on_submit=True):
        st.subheader("Add Client")
        name = st.text_input("Client Name")
        contact = st.text_input("Contact")
        paid = st.number_input("Total Paid", 0.0)
        due = st.number_input("Total Due", 0.0)
        if st.form_submit_button("Save Client"):
            clients_df.loc[len(clients_df)] = [name, contact, paid, due]
            save_df(clients_df, FILES["clients"])
            st.success("Client saved.")
            st.rerun()

    st.dataframe(clients_df)

    st.divider()
    st.subheader("Add Project")

    if clients_df.empty:
        st.info("Please add at least one client first.")
    else:
        with st.form("add_project", clear_on_submit=True):
            client = st.selectbox("Client", clients_df["Client"].unique())
            project = st.text_input("Project Name")
            employee = st.text_input("Assigned Employee")
            budget = st.number_input("Full Budget", 0.0)
            if st.form_submit_button("Save Project"):
                projects_df.loc[len(projects_df)] = [
                    client, project, employee, budget,
                    round(budget * 0.2, 2), round(budget * 0.4, 2), round(budget * 0.4, 2), "Not Paid"
                ]
                save_df(projects_df, FILES["projects"])
                st.success("Project saved.")
                st.rerun()

    st.dataframe(projects_df)

# ─────────────────────── EMPLOYEE SALARIES ───────────────────────
elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    with st.form("add_salary", clear_on_submit=True):
        emp = st.text_input("Employee")
        role = st.text_input("Role")
        sal  = st.number_input("Salary", 0.0)
        paid = st.selectbox("Paid?", ["Yes", "No"])
        dt   = st.date_input("Date", value=date.today())
        if st.form_submit_button("Add Salary"):
            salaries_df.loc[len(salaries_df)] = [emp, role, sal, paid, dt]
            save_df(salaries_df, FILES["salaries"])
            st.rerun()
    st.dataframe(salaries_df)

# ─────────────────────── EXPENSES ───────────────────────
elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    with st.form("add_expense", clear_on_submit=True):
        cat = st.text_input("Category")
        amt = st.number_input("Amount", 0.0)
        dt = st.date_input("Date", value=date.today())
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Expense"):
            expenses_df.loc[len(expenses_df)] = [cat, amt, dt, notes]
            save_df(expenses_df, FILES["expenses"])
            st.rerun()
    st.dataframe(expenses_df)

# ─────────────────────── ANALYTICS ───────────────────────
elif page == "Analytics":
    st.header("📊 Financial Charts")
    fig = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
    st.plotly_chart(fig, use_container_width=True)
    if not projects_df.empty:
        milestone_sum = {
            "20%": projects_df["Payment 20%"].sum(),
            "40%": projects_df["Payment 40%"].sum(),
            "40% (2)": projects_df["Payment 40% (2)"].sum(),
        }
        fig2 = px.pie(values=list(milestone_sum.values()), names=list(milestone_sum.keys()), hole=0.4, title="Project Milestone Payment % Distribution")
        st.plotly_chart(fig2, use_container_width=True)
    if not expenses_df.empty:
        exp_sum = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(exp_sum, values="Amount", names="Category", title="Expense Breakdown by Category", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────── INVOICE GENERATOR ───────────────────────
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

elif page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    st.write("Generate invoices manually or track monthly payment plans.")
    # Add logic from Monthly Plans section here for reuse if needed

# ─────────────────────── MONTHLY PLANS ───────────────────────
elif page == "Monthly Plans":
    st.header("📅 Monthly Payment Plans")
    with st.form("add_monthly", clear_on_submit=True):
        st.subheader("Add Monthly Plan")
        client = st.selectbox("Client", clients_df["Client"].unique())
        amount = st.number_input("Payment Amount", 0.0)
        method = st.selectbox("Payment Method", ["Fast Pay", "Zain Cash", "FIB", "Money Transfer", "Bank Transfer"])
        sm_budget = st.checkbox("Includes Social Media Sponsorship Budget")
        paid = st.selectbox("Is Paid?", ["No", "Yes"])
        if st.form_submit_button("Save Monthly Plan"):
            new_row = {
                "Client": client,
                "Amount": amount,
                "Payment Method": method,
                "Social Media Budget": "Yes" if sm_budget else "No",
                "Paid": paid,
                "Month": date.today().strftime("%B %Y")
            }
            monthly_df.loc[len(monthly_df)] = new_row
            monthly_df.to_csv(FILES["monthly"], index=False)
            st.success("Monthly Plan saved.")
            st.rerun()

    st.subheader("📋 Current Month Summary")
    st.dataframe(monthly_df[monthly_df["Month"] == date.today().strftime("%B %Y")])

    unpaid = monthly_df[(monthly_df["Paid"] == "No") & (monthly_df["Month"] == date.today().strftime("%B %Y"))]
    if not unpaid.empty:
        st.subheader("🚨 Unpaid Clients")
        for i, row in unpaid.iterrows():
            with st.expander(f"{row['Client']} — ${row['Amount']:.2f}"):
                if st.button(f"📄 Generate Payment Request — {row['Client']}", key=f"invoice_{i}"):
                    pdf = InvoicePDF()
                    pdf.add_page()
                    pdf.monthly_invoice(row)
                    filename = f"MonthlyInvoice_{row['Client'].replace(' ', '_')}_{row['Month'].replace(' ', '_')}.pdf"
                    path = INV_DIR / filename
                    pdf.output(str(path))
                    st.download_button("📥 Download PDF", open(path, "rb"), file_name=filename)
                    st.success("PDF Created")

    st.divider()
    st.subheader("✏️ Edit Monthly Plans")
    edited_df = st.data_editor(monthly_df, num_rows='dynamic', use_container_width=True, key="edit_monthly")
    if not edited_df.equals(monthly_df):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Confirm Save Changes"):
                edited_df.to_csv(FILES["monthly"], index=False)
                st.success("Saved successfully.")
        with col2:
            if st.button("↩ Undo Changes"):
                st.rerun()
