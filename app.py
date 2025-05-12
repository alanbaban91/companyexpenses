"""
Agency Finance & Content Calendar Dashboard • 33Studio • May 2025
────────────────────────────────────────────────────────────────────
• CSV‑backed editable tables
• Compact Plotly charts for analytics
• PDF invoice generator

SET‑UP
1. *(optional)* Create & activate a venv:
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux or .\\venv\\Scripts\\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install --upgrade streamlit pandas plotly fpdf
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```
"""

from __future__ import annotations
from datetime import date, time
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(creds)

_sheet_cache: dict[str, gspread.Spreadsheet] = {}

def ws_open(name: str) -> gspread.Worksheet:
    if name not in _sheet_cache:
        _sheet_cache[name] = gc.open_by_key(st.secrets["gsheets"][name]).sheet1
    return _sheet_cache[name]

def load_df(name: str) -> pd.DataFrame:
    df = get_as_dataframe(ws_open(name), evaluate_formulas=True, dtype=str)
    return df.dropna(how="all").reset_index(drop=True)

def save_df(name: str, df: pd.DataFrame):
    ws = ws_open(name)
    ws.clear()
    set_with_dataframe(ws, df)


# ─────────────────────────── PATHS & INITIALIZATION ─────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {name: DATA_DIR / f"{name}.csv" for name in [
    "clients", "projects", "salaries", "expenses", "schedule"
]}

COLUMNS: Dict[str, list[str]] = {
    "clients":  ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Base Fee", "Social Boost", "TVC", "Other", "Total", "Status", "Deadline"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "schedule": ["Client", "Platform", "Post Type", "Date", "Time", "Caption", "Asset Link"],
}

# ensure CSVs exist with correct headers
for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

# ─────────────────────────── LOAD DATA ─────────────────────────
clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"], parse_dates=["Deadline"], dayfirst=True)
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"], dayfirst=True)
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"], dayfirst=True)
schedule_df = pd.read_csv(FILES["schedule"], parse_dates=["Date"], dayfirst=True)

# ─────────────────────────── HELPERS ─────────────────────────
def save_df(df: pd.DataFrame, csv: Path) -> None:
    """Persist DataFrame to its CSV."""
    df.to_csv(csv, index=False)


def add_row(df: pd.DataFrame, csv: Path, row: dict) -> None:
    """Add new row and save."""
    df.loc[len(df)] = row
    save_df(df, csv)


def money(amount: float|int) -> str:
    """Format number as currency."""
    return f"${amount:,.2f}"


def editable_table(label: str, df: pd.DataFrame, csv: Path, key: str) -> pd.DataFrame:
    """Render editable data editor and save changes."""
    edited = st.data_editor(df, key=key, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        save_df(edited, csv)
        st.toast(f"{label} updated", icon="✅")
    return edited

# unified rerun helper
if hasattr(st, "rerun"):
    _rerun = st.rerun
elif hasattr(st, "experimental_rerun"):
    _rerun = st.experimental_rerun
else:
    def _rerun():
        st.warning("Please manually refresh the page to see updates.")

# ─────────────────────────── UI CONFIG ─────────────────────────
st.set_page_config(page_title="33Studio Dashboard", page_icon="📊", layout="wide")
st.title("📊 33Studio — Finance & Content Dashboard")

page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Social Media Calendar", "Invoice", "Analytics"
])

# ─────────────────────────── PAGE: DASHBOARD ─────────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    # ensure numeric types
    for col in ("Total Paid", "Total Due"):  
        clients_df[col] = pd.to_numeric(clients_df[col], errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    total_income     = clients_df["Total Paid"].sum()
    total_due        = clients_df["Total Due"].sum()
    paid_salaries    = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_salaries  = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_expenses   = expenses_df["Amount"].sum() + paid_salaries
    money_left       = total_income - total_expenses

    # Display metrics with an extra column for 'Money Left'
    cols = st.columns(6)
    metrics = [
        ("Income", total_income),
        ("Outstanding", total_due),
        ("Expenses", total_expenses),
        ("Paid Salaries", paid_salaries),
        ("Unpaid Salaries", unpaid_salaries),
        ("Money Left", money_left)
    ]
    for col_box, (label, val) in zip(cols, metrics):
        col_box.metric(label, money(val))

elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    # Add client form
    with st.form("form_add_client", clear_on_submit=True):
        st.subheader("Add / Update Client")
        name    = st.text_input("Client Name")
        contact = st.text_input("Contact Info")
        paid    = st.number_input("Total Paid", min_value=0.0)
        due     = st.number_input("Total Due", min_value=0.0)
        if st.form_submit_button("Save Client"):
            add_row(clients_df, FILES["clients"], {"Client": name, "Contact": contact, "Total Paid": paid, "Total Due": due})
            _rerun()
    clients_df = editable_table("Clients", clients_df, FILES["clients"], "edit_clients")

    st.divider()
    st.subheader("Add Project")
    if clients_df.empty:
        st.info("Please add at least one client first.")
    else:
        with st.form("form_add_project", clear_on_submit=True):
            cl    = st.selectbox("Client", clients_df["Client"].unique())
            proj  = st.text_input("Project Name")
            emp   = st.text_input("Assigned Employee")
            base  = st.number_input("Base Fee", min_value=0.0)
            boost = st.number_input("Social Boost", min_value=0.0)
            tvc   = st.number_input("TVC Budget", min_value=0.0)
            other = st.number_input("Other Fees", min_value=0.0)
            status= st.selectbox("Status", ["Not started","In Progress","Completed"])
            ddl   = st.date_input("Deadline", value=date.today())
            if st.form_submit_button("Save Project"):
                total = base + boost + tvc + other
                add_row(projects_df, FILES["projects"], {"Client":cl, "Project":proj, "Employee":emp, "Base Fee":base, "Social Boost":boost, "TVC":tvc, "Other":other, "Total":total, "Status":status, "Deadline":ddl})
                _rerun()
    projects_df = editable_table("Projects", projects_df, FILES["projects"], "edit_projects")

# ───────────────────── PAGE: EMPLOYEE SALARIES ─────────────────────
elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    with st.form("form_add_salary", clear_on_submit=True):
        emp_name = st.text_input("Employee Name")
        role     = st.text_input("Role")
        salary   = st.number_input("Salary", min_value=0.0)
        paid     = st.selectbox("Paid?", ["No","Yes"])
        sdate    = st.date_input("Date", value=date.today())
        if st.form_submit_button("Save Salary"):
            add_row(salaries_df, FILES["salaries"], {"Employee":emp_name, "Role":role, "Salary":salary, "Paid":paid, "Date":sdate})
            _rerun()
    salaries_df = editable_table("Salaries", salaries_df, FILES["salaries"], "edit_salaries")

# ───────────────────────── PAGE: EXPENSES ─────────────────────────
elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    with st.form("form_add_expense", clear_on_submit=True):
        category = st.text_input("Category")
        amount   = st.number_input("Amount", min_value=0.0)
        edate    = st.date_input("Date", value=date.today())
        notes    = st.text_area("Notes")
        if st.form_submit_button("Save Expense"):
            add_row(expenses_df, FILES["expenses"], {"Category":category, "Amount":amount, "Date":edate, "Notes":notes})
            _rerun()
    expenses_df = editable_table("Expenses", expenses_df, FILES["expenses"], "edit_expenses")

# ───────────────────── PAGE: SOCIAL MEDIA CALENDAR ─────────────────────
elif page == "Social Media Calendar":
    st.header("📆 Social-Media Calendar")
    if clients_df.empty:
        st.info("Add a client first to schedule posts.")
    else:
        with st.form("form_add_post", clear_on_submit=True):
            cl    = st.selectbox("Client", clients_df["Client"].unique())
            plat  = st.selectbox("Platform", ["Instagram","Facebook","TikTok","LinkedIn"])
            ptype = st.text_input("Post Type")
            pdate = st.date_input("Date", value=date.today())
            ptime = st.time_input("Time", value=time(9,0))
            caption = st.text_area("Caption")
            link    = st.text_input("Asset Link (optional)")
            if st.form_submit_button("Schedule Post"):
                add_row(schedule_df, FILES["schedule"], {"Client":cl, "Platform":plat, "Post Type":ptype, "Date":pdate, "Time":ptime.strftime("%H:%M:%S"), "Caption":caption, "Asset Link":link})
                _rerun()
    schedule_df = editable_table("Schedule", schedule_df, FILES["schedule"], "edit_schedule")

# ───────────────────── PAGE: INVOICE GENERATOR ─────────────────────
elif page == "Invoice":  # renamed from 'Invoice Generator'
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.info("No projects available. Please add a project first.")
    else:
        client_sel = st.selectbox("Client", projects_df["Client"].unique())
        proj_sel   = st.selectbox("Project", projects_df[projects_df["Client"]==client_sel]["Project"].unique())
        if st.button("Generate Invoice"):            
            filtered = projects_df[(projects_df["Client"]==client_sel) & (projects_df["Project"]==proj_sel)]
            if filtered.empty:
                st.error("Selected project not found.")
            else:
                row = filtered.iloc[0]
                pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial","B",16)
                pdf.cell(0,10,"INVOICE",ln=True,align="C"); pdf.ln(5)
                pdf.set_font("Arial",size=12)
                for col,val in row.items(): pdf.multi_cell(0,8,f"{col}: {val}")
                fname = f"invoice_{client_sel}_{proj_sel}.pdf".replace(" ","_")
                fpath = INV_DIR / fname
                pdf.output(str(fpath))
                with open(fpath,"rb") as f: st.download_button("Download Invoice", f, file_name=fname, mime="application/pdf")
                st.success("Invoice created.")

# ───────────────────── PAGE: ANALYTICS ─────────────────────
elif page == "Analytics":
    st.header("📊 Analytics Charts")
    # small bar chart income vs expenses
    inc = clients_df["Total Paid"].sum()
    exp_total = expenses_df["Amount"].sum() + salaries_df.query("Paid=='Yes'")["Salary"].sum()
    fig1 = px.bar(x=["Income","Expenses"], y=[inc,exp_total], title="Income vs Expenses", width=350, height=300)
    # pie chart expense breakdown
    fig2, fig3 = None, None
    if not expenses_df.empty:
        brk = expenses_df.groupby("Category")["Amount"].sum()
        fig2 = px.pie(values=brk.values, names=brk.index, hole=0.4, title="Expense Breakdown", width=350, height=300)
    # donut chart project status
    if not projects_df.empty:
        sts = projects_df["Status"].value_counts()
        fig3 = px.pie(values=sts.values, names=sts.index, hole=0.5, title="Project Status", width=350, height=300)
    cols = st.columns(3)
    cols[0].plotly_chart(fig1, use_container_width=False)
    if fig2: cols[1].plotly_chart(fig2, use_container_width=False)
    if fig3: cols[2].plotly_chart(fig3, use_container_width=False)
