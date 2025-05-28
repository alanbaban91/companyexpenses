from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
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
}

COLUMNS = {
    "clients": ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
}

for k, p in FILES.items():
    if not p.exists():
        pd.DataFrame(columns=COLUMNS[k]).to_csv(p, index=False)

clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])

# ─────────────────────── SETUP ───────────────────────
st.set_page_config("33Studio Dashboard", layout="wide")
st.title("📊 33Studio — Finance Dashboard")

page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Invoice Generator", "Analytics"
])

def save_df(df, csv): df.to_csv(csv, index=False)
def money(x): return f"${x:,.2f}"

def add_row(df, csv, row):
    df.loc[len(df)] = row
    save_df(df, csv)

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


elif page == "Monthly Plans":
    st.header("📅 Monthly Payment Plans")
    monthly_file = FILES.get("monthly", DATA_DIR / "monthly.csv")
    monthly_cols = ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"]

    if not monthly_file.exists():
        pd.DataFrame(columns=monthly_cols).to_csv(monthly_file, index=False)

    monthly_df = pd.read_csv(monthly_file)

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
            monthly_df.to_csv(monthly_file, index=False)
            st.success("Monthly Plan saved.")
            st.rerun()

    st.subheader("📋 Current Month Summary")
    st.dataframe(monthly_df[monthly_df["Month"] == date.today().strftime("%B %Y")])
    
# ─────────────────────── Monthly Plans ───────────────────────
    unpaid = monthly_df[(monthly_df["Paid"] == "No") & (monthly_df["Month"] == date.today().strftime("%B %Y"))]
    if not unpaid.empty:
        st.subheader("🚨 Unpaid Clients")
        for i, row in unpaid.iterrows():
            with st.expander(f"{row['Client']} — ${row['Amount']:.2f}"):
                if st.button(f"📄 Generate Payment Request — {row['Client']}", key=f"invoice_{i}"):
                    pdf = InvoicePDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "", 11)
                    pdf.cell(0, 10, f"Payment Request for {row['Client']}", ln=True)
                    pdf.cell(0, 10, f"Amount Due: ${row['Amount']:.2f}", ln=True)
                    pdf.cell(0, 10, f"Payment Method: {row['Payment Method']}", ln=True)
                    pdf.cell(0, 10, f"Due Date: 28 {row['Month']}", ln=True)
                    pdf.ln(5)
                    pdf.cell(0, 10, "Please make the payment by the due date.", ln=True)
                    filename = f"MonthlyInvoice_{row['Client'].replace(' ', '_')}_{row['Month'].replace(' ', '_')}.pdf"
                    path = INV_DIR / filename
                    pdf.output(str(path))
                    st.download_button("📥 Download PDF", open(path, "rb"), file_name=filename)
                    st.success("PDF Created")


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
            add_row(clients_df, FILES["clients"], {
                "Client": name, "Contact": contact, "Total Paid": paid, "Total Due": due
            })
            st.rerun()

    edited_clients_df = st.data_editor(clients_df, num_rows='dynamic', use_container_width=True, key='edit_clients')
    if not edited_clients_df.equals(clients_df):
        if st.button("💾 Confirm Save Clients"):
            save_df(edited_clients_df, FILES["clients"])
            st.success("Clients table updated.")
        if st.button("↩ Undo Changes Clients"):
            st.rerun()
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
                add_row(projects_df, FILES["projects"], {
                    "Client": client, "Project": project, "Employee": employee,
                    "Budget": budget,
                    "Payment 20%": round(budget * 0.2, 2),
                    "Payment 40%": round(budget * 0.4, 2),
                    "Payment 40% (2)": round(budget * 0.4, 2),
                    "Paid Status": "Not Paid"
                })
                st.success("Project saved.")
                st.rerun()

    edited_projects_df = st.data_editor(projects_df, num_rows='dynamic', use_container_width=True, key='edit_projects')
    if not edited_projects_df.equals(projects_df):
        if st.button("💾 Confirm Save Projects"):
            save_df(edited_projects_df, FILES["projects"])
            st.success("Projects table updated.")
        if st.button("↩ Undo Changes Projects"):
            st.rerun()

    st.subheader("💰 Mark Project Payments")
    if not projects_df.empty:
        selected_proj = st.selectbox("Select a Project to Mark Payment", projects_df["Project"].unique())
        milestone_to_mark = st.radio("Mark as Paid", ["Payment 20%", "Payment 40%", "Payment 40% (2)"])
        if st.button("Confirm Payment"):
            idx = projects_df[projects_df["Project"] == selected_proj].index
            if not idx.empty:
                projects_df.loc[idx, milestone_to_mark] = 0
                if all(col in projects_df.columns and projects_df.loc[idx[0], col] == 0 for col in ["Payment 20%", "Payment 40%", "Payment 40% (2)"]):
                    projects_df.loc[idx, "Paid Status"] = "Paid"
                save_df(projects_df, FILES["projects"])
                st.success(f"{milestone_to_mark} marked as paid.")
                st.rerun()

# ─────────────────────── SALARIES ───────────────────────
elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    with st.form("add_salary", clear_on_submit=True):
        emp = st.text_input("Employee")
        role = st.text_input("Role")
        sal  = st.number_input("Salary", 0.0)
        paid = st.selectbox("Paid?", ["Yes", "No"])
        dt   = st.date_input("Date", value=date.today())
        if st.form_submit_button("Add Salary"):
            add_row(salaries_df, FILES["salaries"], {
                "Employee": emp, "Role": role, "Salary": sal, "Paid": paid, "Date": dt
            })
            st.rerun()
    edited_salaries_df = st.data_editor(salaries_df, num_rows='dynamic', use_container_width=True, key='edit_salaries')
    if not edited_salaries_df.equals(salaries_df):
        if st.button("💾 Confirm Save Salaries"):
            save_df(edited_salaries_df, FILES["salaries"])
            st.success("Salaries table updated.")
        if st.button("↩ Undo Changes Salaries"):
            st.rerun()

# ─────────────────────── EXPENSES ───────────────────────
elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    with st.form("add_expense", clear_on_submit=True):
        cat = st.text_input("Category")
        amt = st.number_input("Amount", 0.0)
        dt = st.date_input("Date", value=date.today())
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Expense"):
            add_row(expenses_df, FILES["expenses"], {
                "Category": cat, "Amount": amt, "Date": dt, "Notes": notes
            })
            st.rerun()
    edited_expenses_df = st.data_editor(expenses_df, num_rows='dynamic', use_container_width=True, key='edit_expenses')
    if not edited_expenses_df.equals(expenses_df):
        if st.button("💾 Confirm Save Expenses"):
            save_df(edited_expenses_df, FILES["expenses"])
            st.success("Expenses table updated.")
        if st.button("↩ Undo Changes Expenses"):
            st.rerun()

# ─────────────────────── INVOICES ───────────────────────
class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "33Studio Creative Agency", ln=True)
        self.set_font("Helvetica", size=10)
        self.cell(0, 5, "Erbil, Kurdistan Region, Iraq", ln=True)
        self.cell(0, 5, "Email: hello@33studio.org", ln=True)
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    def invoice_body(self, row, label, amount):
        self.set_font("Helvetica", "", 11)
        self.cell(0, 8, f"Client: {row['Client']}", ln=True)
        self.cell(0, 8, f"Project: {row['Project']}", ln=True)
        self.cell(0, 8, f"Employee: {row['Employee']}", ln=True)
        self.cell(0, 8, f"Milestone: {label} - ${amount:,.2f}", ln=True)
        self.ln(5)
        self.set_font("Helvetica", "B", 12)
        self.cell(100, 8, "Description", border=1)
        self.cell(40, 8, "Amount", border=1, ln=True)
        self.set_font("Helvetica", "", 11)
        self.cell(100, 8, label, border=1)
        self.cell(40, 8, f"${amount:,.2f}", border=1, ln=True)

def create_invoice_pdf(row, label, amount):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.invoice_body(row, label, amount)
    fname = f"Invoice_{row['Client'].replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf"
    fpath = INV_DIR / fname
    pdf.output(str(fpath))
    return fpath

if page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.warning("No projects available.")
    else:
        client = st.selectbox("Client", projects_df["Client"].unique())
        filtered = projects_df[projects_df["Client"] == client]
        project = st.selectbox("Project", filtered["Project"].unique())
        selected = filtered[filtered["Project"] == project].iloc[0]

        milestone_label = None
        amount = 0
        for milestone in ["Payment 20%", "Payment 40%", "Payment 40% (2)"]:
            if milestone in selected and pd.notnull(selected[milestone]) and selected[milestone] > 0:
                milestone_label = milestone
                amount = selected[milestone]
                break
        if milestone_label is None:
            st.success("✅ All payments completed.")
            st.stop()

        st.write(f"Next payment due: **{milestone_label}** — ${amount:,.2f}")
        if st.button("Generate Invoice"):
            fpath = create_invoice_pdf(selected, milestone_label, amount)
            st.download_button("Download Invoice", open(fpath, "rb"), file_name=fpath.name)
            st.success("Invoice generated.")

# ─────────────────────── ANALYTICS ───────────────────────
elif page == "Analytics":
    st.header("📊 Financial Charts")

    # Total Paid per Client
    fig = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
    st.plotly_chart(fig, use_container_width=True)

    # Project Budget Breakdown by Milestone Percentage
    if not projects_df.empty:
        if "Budget" in projects_df.columns:
                projects_df["Budget"] = pd.to_numeric(projects_df["Budget"], errors="coerce").fillna(0)
        milestone_sum = {
            "20%": projects_df["Payment 20%"].sum(),
            "40%": projects_df["Payment 40%"].sum(),
            "40% (2)": projects_df["Payment 40% (2)"].sum(),
        }
        fig2 = px.pie(values=list(milestone_sum.values()), names=list(milestone_sum.keys()), hole=0.4, title="Project Milestone Payment % Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    # Expense Breakdown
    if not expenses_df.empty:
        exp_sum = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(exp_sum, values="Amount", names="Category", title="Expense Breakdown by Category", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
