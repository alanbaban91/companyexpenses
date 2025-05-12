"""
Agency Finance & Content Calendar Dashboard • 33Studio • May 2025
────────────────────────────────────────────────────────────────────
Now fully backed by **Google Sheets** — every change made in the app
is saved instantly to the cloud and shared with your team.

SET‑UP
1. `pip install streamlit pandas plotly fpdf gspread gspread_dataframe google-auth`
2. Add a `.streamlit/secrets.toml` with your service‑account JSON and
   sheet IDs (see README).
3. `streamlit run app.py`
"""

from __future__ import annotations
from datetime import date, time
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from fpdf import FPDF

# ─────────────────────────── GOOGLE SHEETS BACKEND ───────────────────────────
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
gc = gspread.authorize(creds)

_SHEET_CACHE: Dict[str, gspread.Worksheet] = {}

def _ws(name: str) -> gspread.Worksheet:
    """Return (cached) first worksheet for logical sheet name."""
    if name not in _SHEET_CACHE:
        key = st.secrets["gsheets"][name]
        _SHEET_CACHE[name] = gc.open_by_key(key).sheet1
    return _SHEET_CACHE[name]

@st.cache_data(ttl=60)
def load_df(name: str) -> pd.DataFrame:
    df = get_as_dataframe(_ws(name), evaluate_formulas=True, dtype=str)
    return df.dropna(how="all").reset_index(drop=True)

def save_df(name: str, df: pd.DataFrame):
    ws = _ws(name)
    ws.clear()
    set_with_dataframe(ws, df)

# handy wrappers --------------------------------------------------------------

def add_row(name: str, df: pd.DataFrame, row: dict):
    df.loc[len(df)] = row
    save_df(name, df)

def money(x) -> str:
    return f"${float(x):,.2f}"

def editable_table(label: str, name: str, df: pd.DataFrame, key: str):
    edited = st.data_editor(df, key=key, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        save_df(name, edited)
        st.toast(f"{label} updated", icon="✅")
    return edited

# ─────────────────────────── INITIAL DATA LOAD ───────────────────────────
clients_df  = load_df("clients")
projects_df = load_df("projects")
salaries_df = load_df("salaries")
expenses_df = load_df("expenses")
schedule_df = load_df("schedule")

# ─────────────────────────── UI CONFIG ───────────────────────────
st.set_page_config("33Studio Dashboard", page_icon="📊", layout="wide")
st.title("📊 33Studio — Finance & Content Dashboard (Sheets‑backed)")
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries", "Expenses",
    "Social Media Calendar", "Invoice", "Analytics"
])

# ─────────────────────────── DASHBOARD ───────────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics (live from Sheets)")
    for col in ("Total Paid", "Total Due"):
        clients_df[col] = pd.to_numeric(clients_df[col], errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    inc = clients_df["Total Paid"].sum()
    due = clients_df["Total Due"].sum()
    paid_sal = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_sal = salaries_df.query("Paid=='No'")["Salary"].sum()
    exp = expenses_df["Amount"].sum() + paid_sal
    left = inc - exp

    cols = st.columns(6)
    for c,(lbl,val) in zip(cols,[
        ("Income",inc),("Outstanding",due),("Expenses",exp),("Paid Salaries",paid_sal),("Unpaid Salaries",unpaid_sal),("Money Left",left)
    ]):
        c.metric(lbl, money(val))

# ─────────────────────────── CLIENTS & PROJECTS ───────────────────────────
elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    with st.form("add_client", clear_on_submit=True):
        nm = st.text_input("Client Name"); contact = st.text_input("Contact")
        paid = st.number_input("Total Paid", 0.0); due = st.number_input("Total Due", 0.0)
        if st.form_submit_button("Save Client"):
            add_row("clients", clients_df, {"Client":nm,"Contact":contact,"Total Paid":paid,"Total Due":due})
            st.experimental_rerun()
    clients_df = editable_table("Clients", "clients", clients_df, "tbl_clients")

    st.divider(); st.subheader("Add Project")
    if clients_df.empty:
        st.info("Add a client first.")
    else:
        with st.form("add_project", clear_on_submit=True):
            cl = st.selectbox("Client", clients_df["Client"].unique())
            pj = st.text_input("Project"); emp = st.text_input("Employee")
            base = st.number_input("Base Fee",0.0); boost = st.number_input("Social Boost",0.0)
            tvc = st.number_input("TVC",0.0); other = st.number_input("Other",0.0)
            status = st.selectbox("Status",["Not started","In Progress","Completed"])
            ddl = st.date_input("Deadline",value=date.today())
            if st.form_submit_button("Save Project"):
                total = base+boost+tvc+other
                add_row("projects", projects_df, {"Client":cl,"Project":pj,"Employee":emp,"Base Fee":base,"Social Boost":boost,"TVC":tvc,"Other":other,"Total":total,"Status":status,"Deadline":ddl})
                st.experimental_rerun()
    projects_df = editable_table("Projects", "projects", projects_df, "tbl_projects")

# ───────────────────────── OTHER PAGES (Salaries, Expenses, Calendar, Invoice, Analytics) ─────────────────────────
# ... adapt similarly using add_row(<sheet>, df, row) and editable_table(<label>, <sheet>, df, key) ...
