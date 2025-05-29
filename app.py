from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

# ─────────────────────────── FILE & FOLDER SETUP ───────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
INV_DIR  = BASE_DIR / "invoices"; INV_DIR.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    "clients":   DATA_DIR / "clients.csv",
    "projects":  DATA_DIR / "projects.csv",
    "salaries":  DATA_DIR / "salaries.csv",
    "expenses":  DATA_DIR / "expenses.csv",
    "monthly":   DATA_DIR / "monthly.csv",
}

COLUMNS = {
    "clients":   ["Client", "Contact", "Total Paid", "Total Due"],
    "projects":  ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries":  ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses":  ["Category", "Amount", "Date", "Notes"],
    "monthly":   ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"],
}

# Ensure CSVs exist
for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

# Load data
clients_df   = pd.read_csv(FILES["clients"])
projects_df  = pd.read_csv(FILES["projects"])
salaries_df  = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
expenses_df  = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
monthly_df   = pd.read_csv(FILES["monthly"])

# ─────────────────────────── HELPERS ───────────────────────────
def save_df(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False)

def money(x: float|int) -> str:
    return f"${x:,.2f}"

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
        text = (
            f"Payment Request for {row['Client']}\n"
            f"Amount Due: {money(row['Amount'])}\n"
            f"Payment Method: {row['Payment Method']}\n"
            f"Due Date: 28 {row['Month']}\n\n"
            "Please make the payment by the due date."
        )
        self.multi_cell(0, 10, text)
    def build_milestone(self, row, label, amount):
        self.set_font("Helvetica", size=11)
        text = (
            f"Client: {row['Client']}\n"
            f"Project: {row['Project']}\n"
            f"Employee: {row['Employee']}\n"
            f"Milestone: {label} – {money(amount)}\n\n"
            "Kindly settle the above amount at your earliest convenience."
        )
        self.multi_cell(0, 10, text)

# ─────────────────────────── STREAMLIT CONFIG ───────────────────────────
st.set_page_config("33Studio Dashboard", layout="wide")
st.title("📊 33Studio — Finance Dashboard")

page = st.sidebar.radio("Navigate", [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Monthly Plans", "Invoice Generator", "Analytics"
])

# ─────────────────────────── DASHBOARD ───────────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    # Cast to numeric
    clients_df[["Total Paid","Total Due"]] = (
        clients_df[["Total Paid","Total Due"]]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    income      = clients_df["Total Paid"].sum()
    outstanding = clients_df["Total Due"].sum()
    paid_sal    = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_sal  = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_exp   = expenses_df["Amount"].sum() + paid_sal

    cols = st.columns(5)
    metrics = [
        ("Income", income),
        ("Outstanding", outstanding),
        ("Expenses", total_exp),
        ("Paid Salaries", paid_sal),
        ("Unpaid Salaries", unpaid_sal),
    ]
    for col_box, (lbl, val) in zip(cols, metrics):
        col_box.metric(lbl, money(val))

# ───────────────────── CLIENTS & PROJECTS ─────────────────────
elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    # Add client
    with st.expander("➕ Add Client"):
        with st.form("add_client", clear_on_submit=True):
            nm = st.text_input("Client Name")
            ct = st.text_input("Contact Info")
            tp = st.number_input("Total Paid", 0.0)
            td = st.number_input("Total Due", 0.0)
            if st.form_submit_button("Save Client"):
                clients_df.loc[len(clients_df)] = [nm, ct, tp, td]
                save_df(clients_df, FILES["clients"])
                st.success("Client saved.")
                st.rerun()

    # Edit clients
    clients_df = st.data_editor(clients_df, use_container_width=True, key="edit_clients")
    if st.button("💾 Save Clients"):
        save_df(clients_df, FILES["clients"])
        st.success("Clients table updated.")

    st.divider()

    # Add project
    with st.expander("➕ Add Project"):
        if clients_df.empty:
            st.info("Please add at least one client first.")
        else:
            with st.form("add_project", clear_on_submit=True):
                cl = st.selectbox("Client", clients_df["Client"].unique())
                pr = st.text_input("Project Name")
                em = st.text_input("Assigned Employee")
                bu = st.number_input("Budget", 0.0)
                if st.form_submit_button("Save Project"):
                    row = {
                        "Client": cl,
                        "Project": pr,
                        "Employee": em,
                        "Budget": bu,
                        "Payment 20%": round(bu*0.2, 2),
                        "Payment 40%": round(bu*0.4, 2),
                        "Payment 40% (2)": round(bu*0.4, 2),
                        "Paid Status": "Not Paid"
                    }
                    projects_df.loc[len(projects_df)] = row
                    save_df(projects_df, FILES["projects"])
                    st.success("Project saved.")
                    st.rerun()

    # Edit projects
    projects_df = st.data_editor(projects_df, use_container_width=True, key="edit_projects")
    if st.button("💾 Save Projects"):
        save_df(projects_df, FILES["projects"])
        st.success("Projects table updated.")

    # Mark milestone paid
    st.subheader("💰 Mark Milestone Paid")
    if not projects_df.empty:
        sel = st.selectbox("Select Project", projects_df["Project"].unique())
        ms  = st.radio("Milestone", ["Payment 20%", "Payment 40%", "Payment 40% (2)"])
        if st.button("Mark Paid"):
            idx = projects_df[projects_df["Project"]==sel].index
            if idx.any():
                projects_df.at[idx[0], ms] = 0
                r = projects_df.loc[idx[0]]
                if all(r[m]==0 for m in ["Payment 20%","Payment 40%","Payment 40% (2)"]):
                    projects_df.at[idx[0], "Paid Status"] = "Paid"
                save_df(projects_df, FILES["projects"])
                st.success("Milestone updated to paid.")
                st.rerun()

# ───────────────────── EMPLOYEE SALARIES ─────────────────────
elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    with st.expander("➕ Add Salary"):
        with st.form("add_salary", clear_on_submit=True):
            en  = st.text_input("Employee Name")
            ro  = st.text_input("Role")
            sa  = st.number_input("Salary", 0.0)
            pdn = st.selectbox("Paid?", ["No","Yes"])
            dt  = st.date_input("Date", date.today())
            if st.form_submit_button("Save Salary"):
                salaries_df.loc[len(salaries_df)] = [en, ro, sa, pdn, dt]
                save_df(salaries_df, FILES["salaries"])
                st.success("Salary saved.")
                st.rerun()
    salaries_df = st.data_editor(salaries_df, use_container_width=True, key="edit_salaries")
    if st.button("💾 Save Salaries"):
        save_df(salaries_df, FILES["salaries"])
        st.success("Salaries table updated.")

# ───────────────────── EXPENSES ─────────────────────
elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    with st.expander("➕ Add Expense"):
        with st.form("add_expense", clear_on_submit=True):
            ca = st.text_input("Category")
            am = st.number_input("Amount", 0.0)
            dt = st.date_input("Date", date.today())
            no = st.text_area("Notes")
            if st.form_submit_button("Save Expense"):
                expenses_df.loc[len(expenses_df)] = [ca, am, dt, no]
                save_df(expenses_df, FILES["expenses"])
                st.success("Expense saved.")
                st.rerun()
    expenses_df = st.data_editor(expenses_df, use_container_width=True, key="edit_expenses")
    if st.button("💾 Save Expenses"):
        save_df(expenses_df, FILES["expenses"])
        st.success("Expenses table updated.")

# ───────────────────── MONTHLY PLANS ─────────────────────
elif page == "Monthly Plans":
    st.header("📅 Monthly Payment Plans")
    with st.expander("➕ Add Monthly Plan"):
        with st.form("add_monthly", clear_on_submit=True):
            cm = st.selectbox("Client", clients_df["Client"].unique())
            am = st.number_input("Amount", 0.0)
            pm = st.selectbox("Payment Method", ["Fast Pay","Zain Cash","FIB","Money Transfer","Bank Transfer"])
            sb = st.checkbox("Includes Social Media Budget")
            pd = st.selectbox("Paid?", ["No","Yes"])
            if st.form_submit_button("Save Plan"):
                monthly_df.loc[len(monthly_df)] = [
                    cm, am, pm,
                    "Yes" if sb else "No", pd,
                    date.today().strftime("%B %Y")
                ]
                save_df(monthly_df, FILES["monthly"])
                st.success("Monthly plan saved.")
                st.rerun()
    current = monthly_df[monthly_df["Month"]==date.today().strftime("%B %Y")]
    st.dataframe(current, use_container_width=True)
    unpaid  = current[current["Paid"]=="No"]
    if not unpaid.empty:
        st.subheader("🚨 Unpaid Clients")
        for i,row in unpaid.iterrows():
            with st.expander(f"{row['Client']} — {money(row['Amount'])}"):
                if st.button(f"Generate Request — {row['Client']}", key=i):
                    pdf = InvoicePDF(); pdf.add_page(); pdf.build_monthly(row)
                    fn = f"Req_{row['Client']}_{row['Month']}.pdf".replace(" ","_")
                    path = INV_DIR / fn
                    pdf.output(str(path))
                    st.download_button("📥 Download PDF", open(path, "rb"), file_name=fn)
                    st.success("PDF created.")

# ───────────────────── INVOICE GENERATOR ─────────────────────
elif page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.info("No projects available. Please add some first.")
    else:
        cli  = st.selectbox("Client", projects_df["Client"].unique())
        filt = projects_df[projects_df["Client"]==cli]
        prj  = st.selectbox("Project", filt["Project"].unique())
        row  = filt[filt["Project"]==prj].iloc[0]
        # find next milestone
        label, amt = None, 0
        for m in ["Payment 20%","Payment 40%","Payment 40% (2)"]:
            if row[m] > 0:
                label, amt = m, row[m]
                break
        if label:
            st.write(f"Next due: **{label}** — {money(amt)}")
            if st.button("Generate Invoice"):
                pdf = InvoicePDF(); pdf.add_page(); pdf.build_milestone(row, label, amt)
                fn   = f"Inv_{cli}_{label}.pdf".replace(" ","_")
                path = INV_DIR / fn
                pdf.output(str(path))
                st.download_button("📥 Download Invoice", open(path, "rb"), file_name=fn)
                st.success("Invoice generated.")
        else:
            st.success("✅ All milestones paid.")

# ───────────────────── ANALYTICS ─────────────────────
elif page == "Analytics":
    st.header("📊 Analytics")
    # Client payments
    fig1 = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
    st.plotly_chart(fig1, use_container_width=True)
    # Milestone distribution
    if not projects_df.empty:
        ms = projects_df[["Payment 20%","Payment 40%","Payment 40% (2)"]].sum()
        fig2 = px.pie(ms, values=ms.values, names=ms.index, hole=0.4, title="Milestone Distribution")
        st.plotly_chart(fig2, use_container_width=True)
    # Expense breakdown
    if not expenses_df.empty:
        exp = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(exp, values="Amount", names="Category", hole=0.4, title="Expenses Breakdown")
        st.plotly_chart(fig3, use_container_width=True)
