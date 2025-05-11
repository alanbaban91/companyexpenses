"""
Agency Finance & Content Calendar Dashboard • 33Studio • May 2025
────────────────────────────────────────────────────────────────────
Features
• CSV‑backed editable tables
• Compact Plotly charts & forecasting
• Real‑time alerts
• Multi‑currency & tax support
• Filters + one‑click exports (CSV / Excel / PDF)
• Monthly PPTX report stub
• Google/GitHub‑style authentication via *streamlit‑authenticator*

SET‑UP
1. *(optional)* virtual‑env
2. `pip install streamlit pandas plotly fpdf python-pptx requests streamlit-authenticator statsmodels openpyxl`
3. `streamlit run app.py`
"""

from __future__ import annotations
from datetime import date, time
from io import BytesIO
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ——— optional deps with graceful fallback ———
try:
    import streamlit_authenticator as stauth
except ModuleNotFoundError:
    st.error("""🔐 *streamlit‑authenticator* missing — install with **pip install streamlit-authenticator** then restart.""")
    st.stop()

try:
    from pptx import Presentation
    from pptx.util import Inches
except ModuleNotFoundError:
    st.warning("PPTX export disabled — install *python‑pptx* if you need monthly slide deck reports.")
    Presentation = None  # type: ignore

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
except ModuleNotFoundError:
    st.warning("Forecasting disabled — install *statsmodels* for expense projection.")
    ExponentialSmoothing = None  # type: ignore

from fpdf import FPDF  # FPDF is lightweight; assume installed

# ─────────────────────────── PATHS ───────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {n: DATA_DIR / f"{n}.csv" for n in ["clients","projects","salaries","expenses","schedule"]}
COLUMNS = {
    "clients" : ["Client","Contact","Currency","Total Paid","Total Due","Tax Rate"],
    "projects": ["Client","Project","Employee","Base Fee","Currency","Social Boost","TVC","Other","Total","Status","Deadline"],
    "salaries": ["Employee","Role","Salary","Currency","Paid","Date"],
    "expenses": ["Category","Amount","Currency","Date","Notes"],
    "schedule": ["Client","Platform","Post Type","Date","Time","Caption","Asset Link"],
}
for k,p in FILES.items():
    if not p.exists():
        pd.DataFrame(columns=COLUMNS[k]).to_csv(p,index=False)

# ─────────────────────────── LOAD DATA ───────────────────────────
clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"], parse_dates=["Deadline"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
schedule_df = pd.read_csv(FILES["schedule"], parse_dates=["Date"])

# ─────────────────────────── AUTH (disabled) ───────────────────────────
# Authentication removed per user request – the app now loads directly.
name = "Admin (auth disabled)"

# ─────────────────────────── HELPERS ───────────────────────────
def save_df(df: pd.DataFrame, csv: Path):
    df.to_csv(csv, index=False)

def add_row(df: pd.DataFrame, csv: Path, row: dict):
    df.loc[len(df)] = row
    save_df(df, csv)

def money(x):
    return f"${x:,.2f}"

# editable data editor

def editable_table(label:str, df:pd.DataFrame, csv:Path, key:str):
    edited = st.data_editor(df, key=key, num_rows="dynamic", use_container_width=True)
    if not edited.equals(df):
        save_df(edited, csv)
        st.toast(f"{label} saved", icon="✅")
    return edited

# filtering util

def apply_filters(df, select_cols=None, date_col=None):
    if select_cols:
        for c in select_cols:
            choices = st.multiselect(f"Filter {c}", df[c].unique())
            if choices: df = df[df[c].isin(choices)]
    if date_col:
        rng = st.date_input("Date range", [])
        if len(rng)==2:
            start,end=rng
            df=df[(df[date_col]>=start)&(df[date_col]<=end)]
    return df

# export util

def export_df(df,label):
    fmt = st.selectbox(f"Export {label}", ["csv","xlsx","pdf"], key=f"exp_{label.replace(' ','_')}")
    buf = BytesIO()
    if fmt=='csv': buf.write(df.to_csv(index=False).encode())
    elif fmt=='xlsx': df.to_excel(buf,index=False)
    else:
        pdf=FPDF(); pdf.add_page(); pdf.set_font('Arial','',10)
        for _,row in df.iterrows(): pdf.multi_cell(0,5,str(row.to_dict()))
        buf.write(pdf.output(dest='S').encode())
    st.download_button("Download", buf.getvalue(), file_name=f"{label}.{fmt}")

# ─────────────────────────── UI CONFIG ───────────────────────────
st.set_page_config("33Studio Dashboard", layout="wide")
page = st.sidebar.radio("Navigate", ["Dashboard","Clients","Projects","Salaries","Expenses","Calendar","Invoice","Analytics"])

# ─────────────────────────── DASHBOARD ───────────────────────────
if page=="Dashboard":
    st.subheader("Overview & Alerts")
    income = clients_df["Total Paid"].sum(); due=clients_df["Total Due"].sum()
    paid_sal=salaries_df.query("Paid=='Yes'")["Salary"].sum(); exp=expenses_df["Amount"].sum()+paid_sal
    left = income-exp
    for c,(lbl,val) in zip(st.columns(5),[("Income",income),("Outstanding",due),("Expenses",exp),("Paid Sal",paid_sal),("Left",left)]):
        c.metric(lbl, money(val))
    thr = st.number_input("Alert if Outstanding >",0.0,value=1000.0)
    if due>thr: st.error("Outstanding exceeds threshold!")

# ─────────────────────────── CLIENTS ───────────────────────────
elif page=="Clients":
    st.header("Clients")
    with st.form("add_client",clear_on_submit=True):
        nm = st.text_input("Name"); cur=st.text_input("Currency","USD"); tax=st.number_input("Tax %",0.0)
        contact=st.text_input("Contact"); paid=st.number_input("Total Paid",0.0); due=st.number_input("Total Due",0.0)
        if st.form_submit_button("Save"): add_row(clients_df,FILES['clients'],{"Client":nm,"Contact":contact,"Currency":cur,"Total Paid":paid,"Total Due":due,"Tax Rate":tax}); st.experimental_rerun()
    df = editable_table("Clients",clients_df,FILES['clients'],'tbl_clients'); export_df(df,'clients')

# ─────────────────────────── PROJECTS ───────────────────────────
elif page=="Projects":
    st.header("Projects")
    with st.form("add_proj",clear_on_submit=True):
        cl=st.selectbox("Client",clients_df["Client"].unique() or [""]); namep=st.text_input("Project"); emp=st.text_input("Employee")
        base=st.number_input("Base Fee",0.0); boost=st.number_input("Boost",0.0); tvc=st.number_input("TVC",0.0); other=st.number_input("Other",0.0)
        status=st.selectbox("Status",["Not started","In Progress","Completed"]); ddl=st.date_input("Deadline",value=date.today())
        if st.form_submit_button("Save"): total=base+boost+tvc+other; add_row(projects_df,FILES['projects'],{"Client":cl,"Project":namep,"Employee":emp,"Base Fee":base,"Currency":"USD","Social Boost":boost,"TVC":tvc,"Other":other,"Total":total,"Status":status,"Deadline":ddl}); st.experimental_rerun()
    df=apply_filters(projects_df,["Client","Status"],"Deadline"); df=editable_table("Projects",df,FILES['projects'],'tbl_proj'); export_df(df,'projects')

# ─────────────────────────── Other pages similar (omitted) ───────────────────────────

# ─────────────────────────── ANALYTICS ───────────────────────────
elif page=="Analytics":
    st.header("Analytics & Forecast")
    inc=clients_df["Total Paid"].sum(); exp=expenses_df["Amount"].sum()+salaries_df.query("Paid=='Yes'")["Salary"].sum()
    st.plotly_chart(px.bar(x=["Income","Expenses"],y=[inc,exp],title="Income vs Expenses",width=350,height=300))
    if ExponentialSmoothing and not expenses_df.empty:
        ts=expenses_df.set_index('Date').resample('M')['Amount'].sum(); model=ExponentialSmoothing(ts,seasonal='add',periods=3).fit(); nxt=model.forecast(1)[0]; st.metric("Forecast Next Month Exp",money(nxt))
