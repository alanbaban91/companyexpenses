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
        self.multi_cell(0, 10, f"Payment Request for {row['Client']}\nAmount Due: ${row['Amount']:.2f}\nPayment Method: {row['Payment Method']}\nDue Date: 28 {row['Month']}\n\nPlease make the payment by the due date.")

# EXPENSES
if page == "Expenses":
    st.header("💸 Monthly Expenses")
    with st.form("add_expense", clear_on_submit=True):
        cat = st.text_input("Category")
        amt = st.number_input("Amount", 0.0)
        dt = st.date_input("Date", value=date.today())
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Expense"):
            expenses_df.loc[len(expenses_df)] = {"Category": cat, "Amount": amt, "Date": dt, "Notes": notes}
            save_df(expenses_df, FILES["expenses"])
            st.success("Expense saved.")
            st.rerun()

    expenses_df = st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, key="edit_expenses")
    if st.button("💾 Save Expenses"): save_df(expenses_df, FILES["expenses"])

# (rest of app logic remains unchanged...)
