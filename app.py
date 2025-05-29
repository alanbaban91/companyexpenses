from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

# ───────────────────────── FILE & FOLDER SETUP ─────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    "clients":  DATA_DIR / "clients.csv",
    "projects": DATA_DIR / "projects.csv",
    "salaries": DATA_DIR / "salaries.csv",
    "expenses": DATA_DIR / "expenses.csv",
    "monthly":  DATA_DIR / "monthly.csv",
}

COLUMNS = {
    "clients":  ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "monthly":  ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"],
}

# Ensure CSVs exist
for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

# Load data
clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
monthly_df  = pd.read_csv(FILES["monthly"])

# Helpers

def save_df(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False)

def money(val: float|int) -> str:
    return f"${val:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "33Studio — Invoice", ln=True, align="C")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    def build_monthly(self, row):
        self.set_font("Helvetica", size=11)
        self.multi_cell(0, 10,
            f"Payment Request for {row['Client']}\n"
            f"Amount Due: {money(row['Amount'])}\n"
            f"Payment Method: {row['Payment Method']}\n"
            f"Due Date: 28 {row['Month']}\n\n"
            "Please make the payment by the due date.")
    def build_milestone(self, row, label, amount):
        self.set_font("Helvetica", size=11)
        self.multi_cell(0, 10,
            f"Client: {row['Client']}\n"
            f"Project: {row['Project']}\n"
            f"Employee: {row['Employee']}\n"
            f"Milestone: {label} - {money(amount)}\n\n"
            "Kindly settle the above amount at your earliest convenience.")

# Streamlit config
st.set_page_config(page_title="33Studio Dashboard", layout="wide")
st.title("📊 33Studio — Finance Dashboard")
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries", "Expenses",
    "Monthly Plans", "Invoice Generator", "Analytics"
])

# Dashboard
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    clients_df[["Total Paid","Total Due"]] = clients_df[["Total Paid","Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)
    income = clients_df["Total Paid"].sum()
    outstanding = clients_df["Total Due"].sum()
    paid_sal = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_sal = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_exp = expenses_df["Amount"].sum() + paid_sal
    cols = st.columns(5)
    for c, (lbl, val) in zip(cols, [
        ("Income", income),("Outstanding", outstanding),
        ("Expenses", total_exp),("Paid Salaries", paid_sal),("Unpaid Salaries", unpaid_sal)
    ]): c.metric(lbl, money(val))

# Clients & Projects
elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    with st.expander("➕ Add Client"):
        with st.form("add_client", clear_on_submit=True):
            n=st.text_input("Name"); c=st.text_input("Contact")
            p=st.number_input("Total Paid",0.0); d=st.number_input("Total Due",0.0)
            if st.form_submit_button("Save"): clients_df.loc[len(clients_df)]=[n,c,p,d]; save_df(clients_df,FILES["clients"]); st.rerun()
    clients_df = st.data_editor(clients_df,use_container_width=True,key="edcli")
    if st.button("Save Clients"): save_df(clients_df,FILES["clients"])
    st.divider()
    with st.expander("➕ Add Project"):
        if clients_df.empty: st.info("Add client first")
        else:
            with st.form("add_proj", clear_on_submit=True):
                cl=st.selectbox("Client",clients_df["Client"]); pr=st.text_input("Project")
                em=st.text_input("Employee"); bu=st.number_input("Budget",0.0)
                if st.form_submit_button("Save"): r={"Client":cl,"Project":pr,"Employee":em,"Budget":bu,
                    "Payment 20%":round(bu*0.2,2),"Payment 40%":round(bu*0.4,2),"Payment 40% (2)":round(bu*0.4,2),"Paid Status":"Not Paid"}
                    ; projects_df.loc[len(projects_df)]=r; save_df(projects_df,FILES["projects"]); st.rerun()
    projects_df = st.data_editor(projects_df,use_container_width=True,key="edproj")
    if st.button("Save Projects"): save_df(projects_df,FILES["projects"])
    st.subheader("💰 Mark Milestone Paid")
    if not projects_df.empty:
        sel=st.selectbox("Project",projects_df["Project"]);
        mil=st.radio("Milestone",["Payment 20%","Payment 40%","Payment 40% (2)"])
        if st.button("Mark Paid"): idx=projects_df[projects_df["Project"]==sel].index; projects_df.loc[idx,mil]=0;
            row=projects_df.loc[idx[0]]; 
            if row["Payment 20%"]==0 and row["Payment 40%"]==0 and row["Payment 40% (2)"]==0: projects_df.loc[idx,"Paid Status"]="Paid"
            ; save_df(projects_df,FILES["projects"]); st.rerun()

# Employee Salaries
elif page=="Employee Salaries":
    st.header("💼 Salaries")
    with st.expander("➕ Add Salary"):
        with st.form("add_sal",clear_on_submit=True):
            e=st.text_input("Employee"); r=st.text_input("Role")
            s=st.number_input("Salary",0.0); pdn=st.selectbox("Paid",["No","Yes"])
            dt=st.date_input("Date",date.today())
            if st.form_submit_button("Save"): salaries_df.loc[len(salaries_df)]=[e,r,s,pdn,dt]; save_df(salaries_df,FILES["salaries"]); st.rerun()
    salaries_df=st.data_editor(salaries_df,use_container_width=True,key="edsal")
    if st.button("Save Salaries"): save_df(salaries_df,FILES["salaries"])

# Expenses
elif page=="Expenses":
    st.header("💸 Expenses")
    with st.expander("➕ Add Expense"):
        with st.form("add_exp",clear_on_submit=True):
            c=st.text_input("Category"); a=st.number_input("Amount",0.0)
            dt=st.date_input("Date",date.today()); n=st.text_area("Notes")
            if st.form_submit_button("Save"): expenses_df.loc[len(expenses_df)]=[c,a,dt,n]; save_df(expenses_df,FILES["expenses"]); st.rerun()
    expenses_df=st.data_editor(expenses_df,use_container_width=True,key="edexp")
    if st.button("Save Expenses"): save_df(expenses_df,FILES["expenses"])

# Monthly Plans
elif page=="Monthly Plans":
    st.header("📅 Monthly Plans")
    with st.expander("➕ Add Plan"):
        with st.form("add_mon",clear_on_submit=True):
            c=st.selectbox("Client",clients_df["Client"])
            am=st.number_input("Amount",0.0); m=st.selectbox("Method",["Fast Pay","Zain Cash","FIB","Money Transfer","Bank Transfer"])
            sb=st.checkbox("Social Media Budget"); pdn=st.selectbox("Paid",["No","Yes"])
            if st.form_submit_button("Save"): monthly_df.loc[len(monthly_df)]=[c,am,m,"Yes" if sb else "No",pdn,date.today().strftime("%B %Y")]; save_df(monthly_df,FILES["monthly"]); st.rerun()
    mdf=monthly_df[monthly_df["Month"]==date.today().strftime("%B %Y")]
    st.dataframe(mdf,use_container_width=True)
    st.subheader("🚨 Unpaid")
    for i,row in mdf[mdf["Paid"]=="No"].iterrows():
        with st.expander(f"{row['Client']} — {money(row['Amount'])}"):
            if st.button(f"Request {row['Client']}",key=i): pdf=InvoicePDF(); pdf.add_page(); pdf.build_monthly(row);
                fname=f"Req_{row['Client']}_{row['Month']}.pdf"; path=INV_DIR/fname; pdf.output(path); st.download_button("Download",open(path,'rb'),file_name=fname)

# Invoice Generator
elif page=="Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty: st.info("Add projects first")
    else:
        cli=st.selectbox("Client",projects_df["Client"]); filt=projects_df[projects_df["Client"]==cli]
        pr=st.selectbox("Project",filt["Project"]); row=filt[filt["Project"]==pr].iloc[0]
        label,amt=None,0
        for m in ["Payment 20%","Payment 40%","Payment 40% (2)"]:
            if row[m]>0: label,amt=m,row[m]; break
        if label:
            st.write(f"Next: {label} — {money(amt)}")
            if st.button("Generate Invoice"):
                pdf=InvoicePDF(); pdf.add_page(); pdf.build_milestone(row,label,amt)
                fn=f"Inv_{cli}_{label}.pdf"; p=INV_DIR/fn; pdf.output(p); st.download_button("Download",open(p,'rb'),file_name=fn)
        else: st.success("All paid")

# Analytics
elif page=="Analytics":
    st.header("📊 Analytics")
    fig1=px.bar(clients_df,x="Client",y="Total Paid",title="Client Payments")
    st.plotly_chart(fig1,use_container_width=True)
    if not projects_df.empty:
        ps=projects_df[["Payment 20%","Payment 40%","Payment 40% (2)"]].sum()
        fig2=px.pie(values=ps.values,names=ps.index,hole=0.4,title="Milestone Distribution")
        st.plotly_chart(fig2,use_container_width=True)
    if not expenses_df.empty:
        es=expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3=px.pie(es,values="Amount",names="Category",hole=0.4,title="Expenses Breakdown")
        st.plotly_chart(fig3,use_container_width=True)
