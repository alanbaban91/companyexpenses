from __future__ import annotations
from datetime import date, time
from io import BytesIO
from pathlib import Path
from typing import Dict
import json

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from fpdf import FPDF
from google.oauth2.service_account import Credentials
from google.cloud import storage

# ─────────────────────────── PATHS ───────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {n: DATA_DIR / f"{n}.csv" for n in ["clients","projects","salaries","expenses","schedule"]}
COLUMNS = {
    "clients" : ["Client","Contact","Total Paid","Total Due"],
    "projects": ["Client","Project","Employee","Base Fee","Social Boost","TVC","Other","Total","Status","Deadline"],
    "salaries": ["Employee","Role","Salary","Paid","Date"],
    "expenses": ["Category","Amount","Date","Notes"],
    "schedule": ["Client","Platform","Post Type","Date","Time","Caption","Asset Link"],
}
for k,p in FILES.items():
    if not p.exists(): pd.DataFrame(columns=COLUMNS[k]).to_csv(p,index=False)

# ─────────────────────────── LOAD DATA ───────────────────────────
clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"], parse_dates=["Deadline"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
schedule_df = pd.read_csv(FILES["schedule"], parse_dates=["Date"])

# ─────────────────────────── PUSH NOTIFICATIONS ───────────────────────────
try:
    PO_USER  = st.secrets["pushover_user_key"]
    PO_TOKEN = st.secrets["pushover_app_token"]
except (st.errors.StreamlitAPIException, KeyError):
    PO_USER = PO_TOKEN = None

def push_notify(message: str):
    st.toast(message, icon="🔔")
    if PO_USER and PO_TOKEN:
        try:
            requests.post(
                "https://api.pushover.net/1/messages.json",
                data={"token": PO_TOKEN, "user": PO_USER, "message": message[:1024]},
                timeout=5,
            )
        except Exception as e:
            st.warning(f"Push failed: {e}")

# ─────────────────────────── GCP SETUP (OPTIONAL) ───────────────────────────
try:
    gcp_info = json.loads(st.secrets["gcp_service_account"]["json"])
    creds = Credentials.from_service_account_info(gcp_info)
    storage_client = storage.Client(credentials=creds, project=gcp_info["project_id"])
except Exception as e:
    creds = storage_client = None
    st.warning(f"GCP not initialized: {e}")

# ─────────────────────────── HELPERS ───────────────────────────
def save_df(df, csv): df.to_csv(csv, index=False)
def add_row(df, csv, row): df.loc[len(df)] = row; save_df(df, csv)
def money(x): return f"${x:,.2f}"
def editable_table(label, df, csv, key):
    edited = st.data_editor(df, key=key, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        save_df(edited, csv)
        push_notify(f"{label} table updated")
    return edited

# ─────────────────────────── UI CONFIG ─────────────────────────
st.set_page_config("33Studio Dashboard", layout="wide")
page = st.sidebar.radio("Navigate", ["Dashboard","Clients","Projects","Salaries","Expenses","Calendar","Invoice","Analytics"])

# ─────────────────────────── DASHBOARD ─────────────────────────
if page == "Dashboard":
    st.header("Overview & Alerts")
    income = clients_df["Total Paid"].sum()
    due = clients_df["Total Due"].sum()
    paid_sal = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    exp = expenses_df["Amount"].sum() + paid_sal
    left = income - exp
    for c, (lbl, val) in zip(st.columns(5), [("Income", income), ("Outstanding", due), ("Expenses", exp), ("Paid Sal", paid_sal), ("Left", left)]):
        c.metric(lbl, money(val))
    thr = st.number_input("Alert if Outstanding >", 0.0, value=1000.0)
    if due > thr:
        push_notify("Outstanding exceeds threshold!")

# (You can continue adding logic for other pages: Clients, Projects, Salaries, etc.)
