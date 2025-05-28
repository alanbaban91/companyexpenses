from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Dict
import json

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from fpdf import FPDF
from google.oauth2.service_account import Credentials

# ─────────────────────── PATHS ───────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    "clients": DATA_DIR / "clients.csv",
    "projects_milestones": DATA_DIR / "projects_milestones.csv",
    "salaries": DATA_DIR / "salaries.csv",
    "expenses": DATA_DIR / "expenses.csv",
}

COLUMNS = {
    "clients": ["Client", "Contact", "Total Paid", "Total Due"],
    "projects_milestones": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
}

for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects_milestones"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])

try:
    PO_USER  = st.secrets["pushover_user_key"]
    PO_TOKEN = st.secrets["pushover_app_token"]
except Exception:
    PO_USER = PO_TOKEN = None

def push_notify(msg):
    st.toast(msg, icon="\U0001F514")
    if PO_USER and PO_TOKEN:
        try:
            requests.post("https://api.pushover.net/1/messages.json", data={
                "token": PO_TOKEN, "user": PO_USER, "message": msg[:1024]
            }, timeout=5)
        except Exception as e:
            st.warning(f"Push failed: {e}")

st.set_page_config("33Studio Dashboard", layout="wide")
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients", "Projects", "Salaries", "Expenses", "Invoice Generator", "Analytics"
])

def save_df(df, csv): df.to_csv(csv, index=False)
def money(x): return f"${x:,.2f}"

if page == "Dashboard":
    st.header("Overview & Alerts")
    income = clients_df["Total Paid"].sum()
    due = clients_df["Total Due"].sum()
    paid_sal = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    exp = expenses_df["Amount"].sum() + paid_sal
    left = income - exp
    for c, (lbl, val) in zip(st.columns(5), [
        ("Income", income), ("Outstanding", due), ("Expenses", exp),
        ("Paid Sal", paid_sal), ("Left", left)
    ]): c.metric(lbl, money(val))
    if st.number_input("Alert if Outstanding >", 0.0, value=1000.0) < due:
        push_notify("Outstanding exceeds threshold!")

elif page == "Clients":
    st.header("Clients")
    edited = st.data_editor(clients_df, key="clients", num_rows="dynamic", column_config={
        "Client": st.column_config.TextColumn(),
        "Contact": st.column_config.TextColumn(),
        "Total Paid": st.column_config.NumberColumn(),
        "Total Due": st.column_config.NumberColumn()
    }, use_container_width=True), "Project": st.column_config.TextColumn(), "Employee": st.column_config.TextColumn(), "Budget": st.column_config.NumberColumn(), "Payment 20%": st.column_config.NumberColumn(), "Payment 40%": st.column_config.NumberColumn(), "Payment 40% (2)": st.column_config.NumberColumn()}, use_container_width=True)
    if not edited.equals(clients_df):
        save_df(edited, FILES["clients"])
        push_notify("Clients table updated")

elif page == "Projects":
    st.header("Project Milestones")
    def auto_calc(row):
        try:
            budget = float(row["Budget"])
            row["Payment 20%"] = round(budget * 0.20, 2)
            row["Payment 40%"] = round(budget * 0.40, 2)
            row["Payment 40% (2)"] = round(budget * 0.40, 2)
        except: pass
        return row

    projects_df = projects_df.apply(auto_calc, axis=1)
    edited = st.data_editor(projects_df, key="milestones", num_rows="dynamic", column_config={"Client": st.column_config.TextColumn(), "Project": st.column_config.TextColumn(), "Employee": st.column_config.TextColumn(), "Budget": st.column_config.NumberColumn(), "Payment 20%": st.column_config.NumberColumn(), "Payment 40%": st.column_config.NumberColumn(), "Payment 40% (2)": st.column_config.NumberColumn()}, use_container_width=True)
    if not edited.equals(projects_df):
        save_df(edited, FILES["projects_milestones"])
        push_notify("Projects table updated")

    if st.button("\U0001F4E6 Close Month & Archive"):
        archive_path = DATA_DIR / f"milestones_{datetime.now():%Y_%m}.csv"
        save_df(projects_df, archive_path)
        pd.DataFrame(columns=COLUMNS["projects_milestones"]).to_csv(FILES["projects_milestones"], index=False)
        st.success(f"Archived to {archive_path.name} and reset new month.")

elif page == "Salaries":
    st.header("Salaries")
    edited = st.data_editor(salaries_df, key="salaries", num_rows="dynamic", column_config={
        "Employee": st.column_config.TextColumn(),
        "Role": st.column_config.TextColumn(),
        "Salary": st.column_config.NumberColumn(),
        "Paid": st.column_config.TextColumn(),
        "Date": st.column_config.DateColumn()
    }, use_container_width=True), "Project": st.column_config.TextColumn(), "Employee": st.column_config.TextColumn(), "Budget": st.column_config.NumberColumn(), "Payment 20%": st.column_config.NumberColumn(), "Payment 40%": st.column_config.NumberColumn(), "Payment 40% (2)": st.column_config.NumberColumn()}, use_container_width=True)
    if not edited.equals(salaries_df):
        save_df(edited, FILES["salaries"])
        push_notify("Salaries updated")

elif page == "Expenses":
    st.header("Expenses")
    edited = st.data_editor(expenses_df, key="expenses", num_rows="dynamic", column_config={
        "Category": st.column_config.TextColumn(),
        "Amount": st.column_config.NumberColumn(),
        "Date": st.column_config.DateColumn(),
        "Notes": st.column_config.TextColumn()
    }, use_container_width=True), "Project": st.column_config.TextColumn(), "Employee": st.column_config.TextColumn(), "Budget": st.column_config.NumberColumn(), "Payment 20%": st.column_config.NumberColumn(), "Payment 40%": st.column_config.NumberColumn(), "Payment 40% (2)": st.column_config.NumberColumn()}, use_container_width=True)
    if not edited.equals(expenses_df):
        save_df(edited, FILES["expenses"])
        push_notify("Expenses updated")

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "33Studio Creative Agency", ln=True, align="L")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, "Erbil, Kurdistan Region, Iraq", ln=True, align="L")
        self.cell(0, 5, "Email: hello@33studio.org", ln=True, align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def invoice_body(self, client, project, budget, payment_due, issue_date):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, f"Invoice for {client}", ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(100, 6, f"Project: {project}", ln=True)
        self.cell(100, 6, f"Issue Date: {issue_date}", ln=True)
        self.cell(100, 6, f"Due Amount: ${payment_due:,.2f}", ln=True)
        self.cell(100, 6, f"Total Project Budget: ${budget:,.2f}", ln=True)
        self.ln(10)
        self.set_font("Helvetica", "B", 10)
        self.cell(100, 8, "Description", border=1)
        self.cell(40, 8, "Amount", border=1, ln=True)
        self.set_font("Helvetica", "", 10)
        self.cell(100, 8, "Milestone Payment", border=1)
        self.cell(40, 8, f"${payment_due:,.2f}", border=1, ln=True)
        self.ln(10)
        self.cell(100, 6, "Please make the payment by the due date.", ln=True)

def create_invoice_pdf(client, project, employee, budget, due_amount):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.invoice_body(client, project, budget, due_amount, datetime.today().strftime("%Y-%m-%d"))
    filename = INV_DIR / f"Invoice_{client.replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf"
    pdf.output(filename)
    return filename

if page == "Invoice Generator":
    st.header("\U0001F4C4 Generate Invoice")
    milestone_df = pd.read_csv(FILES["projects_milestones"])

    valid_clients = milestone_df["Client"].dropna().unique().tolist()
    if not valid_clients:
        st.warning("No valid clients found.")
    else:
        client = st.selectbox("Select Client", valid_clients)
        filtered = milestone_df[milestone_df["Client"] == client]
        valid_projects = filtered["Project"].dropna().unique().tolist()

        if valid_projects:
            project = st.selectbox("Select Project", valid_projects)
            selected = filtered[filtered["Project"] == project]
            if not selected.empty:
                selected = selected.iloc[0]
                due_amount = 0
                if selected["Payment 20%"] != 0:
                    due_amount = selected["Payment 20%"]
                    label = "20% milestone"
                elif selected["Payment 40%"] != 0:
                    due_amount = selected["Payment 40%"]
                    label = "First 40% milestone"
                elif selected["Payment 40% (2)"] != 0:
                    due_amount = selected["Payment 40% (2)"]
                    label = "Final 40% milestone"
                else:
                    st.success("✅ All payments completed for this project.")
                    st.stop()

                st.write(f"Next Payment Due: **{label}** - ${due_amount:,.2f}")
                if st.button("\U0001F9FE Generate Invoice"):
                    path = create_invoice_pdf(
                        client=selected["Client"],
                        project=selected["Project"],
                        employee=selected["Employee"],
                        budget=float(selected["Budget"]),
                        due_amount=float(due_amount)
                    )
                    st.success("Invoice generated!")
                    st.download_button("\U0001F4E5 Download Invoice", open(path, "rb"), file_name=path.name)
            else:
                st.warning("No project found for selected client.")
        else:
            st.warning("No projects available for this client.")

elif page == "Analytics":
    st.header("Client Payments Chart")
    if not clients_df.empty:
        fig = px.bar(clients_df, x="Client", y="Total Paid", title="Payments by Client")
        st.plotly_chart(fig, use_container_width=True)
