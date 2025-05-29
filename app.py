from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = BASE_DIR / "archive"
INV_DIR = BASE_DIR / "invoices"
for d in (DATA_DIR, ARCHIVE_DIR, INV_DIR):
    d.mkdir(exist_ok=True)

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
    "monthly": ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"],
}

for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

clients_df = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
monthly_df = pd.read_csv(FILES["monthly"])

st.set_page_config("33Studio Dashboard", layout="wide")
st.title("33Studio Finance Dashboard")

pages = [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Invoice Generator", "Analytics", "Monthly Plans",
    "🔄 Start New Month", "📁 View Archives"
]
page = st.sidebar.radio("Navigate", pages)

def save_df(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)

def money(x: float) -> str:
    return f"${x:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Invoice", ln=True, align="C")
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    def cell_safe(self, w, h, txt, **kwargs):
        safe = txt.encode("latin-1", "replace").decode("latin-1")
        self.cell(w, h, safe, **kwargs)

if page == "Dashboard":
    st.header("Overview Metrics")
    clients_df[["Total Paid","Total Due"]] = clients_df[["Total Paid","Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)
    inc = clients_df["Total Paid"].sum()
    out = clients_df["Total Due"].sum()
    paid_sal = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    exp = expenses_df["Amount"].sum() + paid_sal
    cols = st.columns(4)
    cols[0].metric("Income", money(inc))
    cols[1].metric("Outstanding", money(out))
    cols[2].metric("Paid Salaries", money(paid_sal))
    cols[3].metric("Expenses", money(exp))

elif page == "Clients & Projects":
    st.header("Clients & Projects")
    with st.expander("Add Client"):  
        with st.form("fc"):  
            n=st.text_input("Name")
            c=st.text_input("Contact")
            p=st.number_input("Paid",0.0)
            d=st.number_input("Due",0.0)
            if st.form_submit_button("Save"):  
                clients_df.loc[len(clients_df)]=[n,c,p,d]
                save_df(clients_df,FILES["clients"])
                st.experimental_rerun()
    cf=st.data_editor(clients_df,use_container_width=True,num_rows="dynamic",key="cft")
    if not cf.equals(clients_df) and st.button("Save Clients"):  
        save_df(cf,FILES["clients"])
        st.experimental_rerun()
    st.markdown("---")
    st.subheader("Projects")
    with st.expander("Add Project"):  
        with st.form("fp"):  
            if clients_df.empty: st.info("Add client first.")
            else:
                cli=st.selectbox("Client",clients_df["Client"].unique())
                pr=st.text_input("Project")
                em=st.text_input("Employee")
                bu=st.number_input("Budget",0.0)
                if st.form_submit_button("Save"):  
                    a=round(bu*0.2,2);b=round(bu*0.4,2)
                    projects_df.loc[len(projects_df)]=[cli,pr,em,bu,a,b,b,"Not Paid"]
                    save_df(projects_df,FILES["projects"])
                    st.experimental_rerun()
    pf=st.data_editor(projects_df,use_container_width=True,num_rows="dynamic",key="pft")
    if not pf.equals(projects_df) and st.button("Save Projects"):  
        save_df(pf,FILES["projects"])
        st.experimental_rerun()
    st.subheader("Mark Payment")
    if not projects_df.empty:
        sel=st.selectbox("Project",projects_df["Project"].unique())
        ms=st.radio("Milestone",["Payment 20%","Payment 40%","Payment 40% (2)"])
        if st.button("Confirm"):  
            ix=projects_df[projects_df["Project"]==sel].index
            projects_df.loc[ix,ms]=0
            if all(projects_df.loc[ix[0],c]==0 for c in ["Payment 20%","Payment 40%","Payment 40% (2)"]):
                projects_df.loc[ix,"Paid Status"]="Paid"
            save_df(projects_df,FILES["projects"])
            st.experimental_rerun()

elif page == "Employee Salaries":
    st.header("Employee Salaries")
    with st.expander("Add Salary"):  
        with st.form("fs"):  
            e=st.text_input("Employee")
            r=st.text_input("Role")
            s=st.number_input("Salary",0.0)
            pd_ = st.selectbox("Paid?",["Yes","No"])
            dt=st.date_input("Date",date.today())
            if st.form_submit_button("Save"):  
                salaries_df.loc[len(salaries_df)]=[e,r,s,pd_,dt]
                save_df(salaries_df,FILES["salaries"])
                st.experimental_rerun()
    sf=st.data_editor(salaries_df,use_container_width=True,num_rows="dynamic",key="sft")
    if not sf.equals(salaries_df) and st.button("Save Salaries"):  
        save_df(sf,FILES["salaries"])
        st.experimental_rerun()

elif page == "Expenses":
    st.header("Expenses")
    with st.expander("Add Expense"):  
        with st.form("fe"):  
            cat=st.text_input("Category")
            am=st.number_input("Amount",0.0)
            dt=st.date_input("Date",date.today())
            nt=st.text_area("Notes")
            if st.form_submit_button("Save"):  
                expenses_df.loc[len(expenses_df)]=[cat,am,dt,nt]
                save_df(expenses_df,FILES["expenses"])
                st.experimental_rerun()
    ef=st.data_editor(expenses_df,use_container_width=True,num_rows="dynamic",key="eft")
    if not ef.equals(expenses_df) and st.button("Save Expenses"):  
        save_df(ef,FILES["expenses"])
        st.experimental_rerun()

elif page == "Invoice Generator":
    st.header("Invoice Generator")
    if projects_df.empty: st.info("No projects.")
    else:
        cli=st.selectbox("Client",projects_df["Client"].unique())
        pr=st.selectbox("Project",projects_df[projects_df["Client"]==cli]["Project"].unique())
        row=projects_df[(projects_df["Client"]==cli)&(projects_df["Project"]==pr)].iloc[0]
        for m in ["Payment 20%","Payment 40%","Payment 40% (2)"]:
            if row[m]>0:
                ms=m;amt=row[m];break
        else:
            st.success("All paid.");st.stop()
        st.write(f"Next: {ms} = {money(amt)}")
        if st.button("Generate"):  
            pdf=InvoicePDF();pdf.add_page()
            pdf.cell_safe(0,10,f"Client: {cli}",ln=True)
            pdf.cell_safe(0,10,f"Project: {pr}",ln=True)
            pdf.cell_safe(0,10,f"Milestone: {ms} - {money(amt)}",ln=True)
            fn=f"inv_{cli.replace(' ','_')}_{datetime.now():%Y%m%d}.pdf"
            fp=INV_DIR/fn
            pdf.output(str(fp))
            st.download_button("Download",open(fp,'rb'),file_name=fn)

elif page == "Analytics":
    st.header("Analytics")
    if not clients_df.empty:
        fig=px.bar(clients_df,x="Client",y="Total Paid",title="Payments")
        st.plotly_chart(fig,use_container_width=True)
    if not projects_df.empty:
        projects_df["Budget"]=pd.to_numeric(projects_df["Budget"],errors="coerce").fillna(0)
        sums={"20%":projects_df["Payment 20%"].sum(),"40%":projects_df["Payment 40%"].sum(),"40%(2)":projects_df["Payment 40% (2)"].sum()}
        fig2=px.pie(values=list(sums.values()),names=list(sums.keys()),hole=0.4)
        st.plotly_chart(fig2,use_container_width=True)
    if not expenses_df.empty:
        es=expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3=px.pie(es,values="Amount",names="Category",hole=0.4)
        st.plotly_chart(fig3,use_container_width=True)

elif page == "Monthly Plans":
    st.header("Monthly Plans")
    mth=date.today().strftime("%B %Y")
    with st.expander("Add Plan"):  
        with st.form("fm"):  
            cli=st.selectbox("Client",clients_df["Client"].unique())
            amt=st.number_input("Amount",0.0)
            pm=st.selectbox("Method",["Fast Pay","Zain Cash","FIB","Money Transfer","Bank Transfer"])
            sm=st.checkbox("Include Social Media Budget")
            pd_=st.selectbox("Paid?",["No","Yes"])
            if st.form_submit_button("Save"):  
                monthly_df.loc[len(monthly_df)]=[cli,amt,pm,"Yes" if sm else "No",pd_,mth]
                save_df(monthly_df,FILES["monthly"])
                st.experimental_rerun()
    md=st.dataframe(monthly_df[monthly_df["Month"]==mth],use_container_width=True)

elif page == "🔄 Start New Month":
    st.header("Start New Month")
    mth=date.today().strftime("%B_%Y")
    if st.button("Archive and Reset"):  
        archive_file=ARCHIVE_DIR/f"monthly_{mth}.csv"
        monthly_df.to_csv(archive_file,index=False)
        pd.DataFrame(columns=COLUMNS["monthly"]).to_csv(FILES["monthly"],index=False)
        st.success("Archived & reset.")
        st.experimental_rerun()

elif page == "📁 View Archives":
    st.header("View Archives")
    archives=list(ARCHIVE_DIR.glob("monthly_*.csv"))
    sel=st.selectbox("Archive File",[p.name for p in archives])
    if sel:
        df=pd.read_csv(ARCHIVE_DIR/sel)
        st.dataframe(df,use_container_width=True)
