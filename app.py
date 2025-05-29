```python
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
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR = BASE_DIR / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)
INV_DIR = BASE_DIR / "invoices"
INV_DIR.mkdir(exist_ok=True)

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

# Ensure CSVs exist
for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

# Load data
clients_df = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
monthly_df = pd.read_csv(FILES["monthly"])

# Streamlit setup
st.set_page_config("33Studio Dashboard", layout="wide")
st.title("📊 33Studio — Finance Dashboard")

# Sidebar navigation
pages = [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Invoice Generator", "Analytics", "Monthly Plans",
    "🔄 Start New Month", "📁 View Archives"
]
page = st.sidebar.radio("Navigate", pages)

# Helpers

def save_df(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)

def money(val: float) -> str:
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

    def add_line(self, text: str) -> None:
        self.set_font("Helvetica", size=11)
        safe = text.encode("latin-1", "replace").decode("latin-1")
        self.cell(0, 10, safe, ln=True)

    def monthly_invoice(self, row: pd.Series) -> None:
        lines = [
            f"Payment Request for {row['Client']}",
            f"Amount Due: ${row['Amount']:.2f}",
            f"Payment Method: {row['Payment Method']}",
            f"Due Date: 28 {row['Month']}",
            "",
            "Please make the payment by the due date."
        ]
        for line in lines:
            self.add_line(line)

# ─────────────────────── PAGE LOGIC ───────────────────────

if page == "Dashboard":
    st.header("📈 Overview Metrics")
    # numeric conversions
    clients_df[["Total Paid","Total Due"]]=clients_df[["Total Paid","Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    income = clients_df["Total Paid"].sum()
    due    = clients_df["Total Due"].sum()
    paid_sal   = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_sal = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_exp  = expenses_df["Amount"].sum() + paid_sal

    cols = st.columns(5)
    for col,label, val in zip(cols, ["Income","Outstanding","Expenses","Paid Salaries","Unpaid Salaries"],
                               [income,due,total_exp,paid_sal,unpaid_sal]):
        col.metric(label, money(val))

elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    # Add Client
    with st.expander("➕ Add Client"):  
        with st.form("add_client", clear_on_submit=True):
            cname = st.text_input("Client Name")
            contact = st.text_input("Contact Info")
            paid = st.number_input("Total Paid",0.0)
            due  = st.number_input("Total Due",0.0)
            if st.form_submit_button("Save Client"):
                clients_df.loc[len(clients_df)] = [cname,contact,paid,due]
                save_df(clients_df, FILES["clients"])
                st.experimental_rerun()
    # Editable Clients Table
    edited = st.data_editor(clients_df, use_container_width=True, num_rows="dynamic", key="ed_clients")
    if not edited.equals(clients_df):
        if st.button("💾 Save Clients"):
            save_df(edited, FILES["clients"])
            st.success("Clients updated.")
            st.experimental_rerun()

    st.divider()
    st.subheader("📁 Projects")
    # Add Project
    with st.expander("➕ Add Project"):  
        with st.form("add_project", clear_on_submit=True):
            if clients_df.empty:
                st.info("Add a client first.")
            else:
                c = st.selectbox("Client", clients_df["Client"].unique())
                proj = st.text_input("Project Name")
                emp  = st.text_input("Employee")
                bud  = st.number_input("Budget",0.0)
                if st.form_submit_button("Save Project"):
                    p20 = round(bud*0.2,2)
                    p40 = round(bud*0.4,2)
                    projects_df.loc[len(projects_df)] = [c,proj,emp,bud,p20,p40,p40,"Not Paid"]
                    save_df(projects_df, FILES["projects"])
                    st.success("Project added.")
                    st.experimental_rerun()
    # Editable Projects Table
    edited_p = st.data_editor(projects_df, use_container_width=True, num_rows="dynamic", key="ed_projects")
    if not edited_p.equals(projects_df):
        if st.button("💾 Save Projects"):
            save_df(edited_p, FILES["projects"])
            st.success("Projects updated.")
            st.experimental_rerun()

    st.subheader("💰 Mark Payments")
    if not projects_df.empty:
        sel = st.selectbox("Project to mark paid", projects_df["Project"].unique())
        ms  = st.radio("Milestone", ["Payment 20%","Payment 40%","Payment 40% (2)"])
        if st.button("Confirm Payment"):
            idx = projects_df[projects_df["Project"]==sel].index
            projects_df.loc[idx, ms] = 0
            if all(projects_df.loc[idx[0],col]==0 for col in ["Payment 20%","Payment 40%","Payment 40% (2)"]):
                projects_df.loc[idx, "Paid Status"] = "Paid"
            save_df(projects_df, FILES["projects"])
            st.success(f"{ms} marked paid.")
            st.experimental_rerun()

elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    with st.expander("➕ Add Salary"):  
        with st.form("add_sal", clear_on_submit=True):
            emp = st.text_input("Employee")
            role = st.text_input("Role")
            sal  = st.number_input("Salary",0.0)
            paid = st.selectbox("Paid?",["Yes","No"])
            dt   = st.date_input("Date", value=date.today())
            if st.form_submit_button("Save Salary"):
                salaries_df.loc[len(salaries_df)] = [emp,role,sal,paid,dt]
                save_df(salaries_df, FILES["salaries"])
                st.success("Salary added.")
                st.experimental_rerun()
    edited_s = st.data_editor(salaries_df, use_container_width=True, num_rows="dynamic", key="ed_salaries")
    if not edited_s.equals(salaries_df):
        if st.button("💾 Save Salaries"):
            save_df(edited_s, FILES["salaries"])
            st.success("Salaries updated.")
            st.experimental_rerun()

elif page == "Expenses":
    st.header("💸 Expenses")
    with st.expander("➕ Add Expense"):  
        with st.form("add_exp", clear_on_submit=True):
            cat = st.text_input("Category")
            amt = st.number_input("Amount",0.0)
            dt  = st.date_input("Date", value=date.today())
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Expense"):
                expenses_df.loc[len(expenses_df)] = [cat,amt,dt,notes]
                save_df(expenses_df, FILES["expenses"])
                st.success("Expense added.")
                st.experimental_rerun()
    edited_e = st.data_editor(expenses_df, use_container_width=True, num_rows="dynamic", key="ed_expenses")
    if not edited_e.equals(expenses_df):
        if st.button("💾 Save Expenses"):
            save_df(edited_e, FILES["expenses"])
            st.success("Expenses updated.")
            st.experimental_rerun()

elif page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.warning("No projects available.")
    else:
        c = st.selectbox("Client", projects_df["Client"].unique())
        sub = projects_df[projects_df["Client"]==c]
        p = st.selectbox("Project", sub["Project"].unique())
        sel = sub[sub["Project"]==p].iloc[0]

        label,amt = None,0
        for m in ["Payment 20%","Payment 40%","Payment 40% (2)"]:
            if sel[m]>0:
                label,amt = m, sel[m]
                break
        if label:
            st.write(f"Next due: **{label}** — {money(amt)}")
            if st.button("Generate Invoice"):
                pdf = InvoicePDF(); pdf.add_page()
                pdf.add_line(f"Invoice for {sel['Client']}: {label}")
                pdf.add_line(f"Project: {sel['Project']} | Amount: ${amt:,.2f}")
                fname = f"Invoice_{sel['Client'].replace(' ','_')}_{datetime.now():%Y%m%d}.pdf"
                path = INV_DIR / fname
                pdf.output(str(path))
                st.download_button("Download", open(path,'rb'), file_name=fname)
        else:
            st.success("✅ All payments completed.")

elif page == "Analytics":
    st.header("📊 Analytics")
    # Client bar
    if not clients_df.empty:
        fig1 = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payments")
        st.plotly_chart(fig1, use_container_width=True)
    # Milestone pie
    if not projects_df.empty:
        projects_df["Budget"] = pd.to_numeric(projects_df["Budget"], errors="coerce").fillna(0)
        sums = {"20%": projects_df["Payment 20%"].sum(),
                "40%": projects_df["Payment 40%"].sum(),
                "40%(2)": projects_df["Payment 40% (2)"].sum()}
        fig2 = px.pie(values=list(sums.values()), names=list(sums.keys()), hole=0.4,
                      title="Milestone Distribution")
        st.plotly_chart(fig2, use_container_width=True)
    # Expense breakdown
    if not expenses_df.empty:
        e = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(e, values="Amount", names="Category", hole=0.4,
                      title="Expenses by Category")
        st.plotly_chart(fig3, use_container_width=True)

elif page == "Monthly Plans":
    st.header("📆 Monthly Plans")
    with st.expander("➕ Add Monthly Plan"):  
        with st.form("add_month", clear_on_submit=True):
            c = st.selectbox("Client", clients_df["Client"].unique())
            amt = st.number_input("Amount",0.0)
            pm = st.selectbox("Payment Method", ["Fast Pay","Zain Cash","FIB","Money Transfer","Bank Transfer"])
            sm = st.checkbox("Includes Social Budget")
            paid = st.selectbox("Paid?", ["No","Yes"])
            if st.form_submit_button("Save Plan"):
                monthly_df.loc[len(monthly_df)] = [
                    c, amt, pm, "Yes" if sm else "No", paid,
                    date.today().strftime("%B %Y")
                ]
                save_df(monthly_df, FILES["monthly"]);
                st.success("Plan added.")
                st.experimental_rerun()
    mp = monthly_df[monthly_df["Month"]==date.today().strftime("%B %Y")]
    st.dataframe(mp, use_container_width=True)

elif page == "🔄 Start New Month":
    st.header("🔄 Start New Month")
    if st.button("📦 Archive Current & Reset"):
        mstr = datetime.now().strftime("%Y-%m")
        for key,file in FILES.items():
            arc = ARCHIVE_DIR/f"{key}_{mstr}.csv"
            df = pd.read_csv(file)
            df.to_csv(arc,index=False)
            pd.DataFrame(columns=COLUMNS[key]).to_csv(file,index=False)
        st.success("Data archived & reset.")
        st.experimental_rerun()

elif page == "📁 View Archives":
    st.header("📁 Archives")
    files = list(ARCHIVE_DIR.glob("*.csv"))
    if files:
        sel = st.selectbox("Archive File", [f.name for f in files])
        df = pd.read_csv(ARCHIVE_DIR/sel)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode(), sel)
        if st.button("⬅ Restore", key="rest2"):
            orig = sel.split("_")[0]
            if orig in FILES:
                df.to_csv(FILES[orig], index=False)
                st.success(f"Restored to {orig}.csv")
    else:
        st.info("No archives found.")
```
