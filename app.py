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

# ─────────────────────── HELPERS ───────────────────────
def save_df(df, path):
    df.to_csv(path, index=False)

def money(x):
    return f"${x:,.2f}"

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

# ─────────────────────── ROUTING ───────────────────────
if page == "Dashboard":
    st.header("📈 Overview Metrics")
    clients_df[["Total Paid", "Total Due"]] = clients_df[["Total Paid", "Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    salaries_df["Salary"] = pd.to_numeric(salaries_df["Salary"], errors="coerce").fillna(0)
    expenses_df["Amount"] = pd.to_numeric(expenses_df["Amount"], errors="coerce").fillna(0)

    total_income = clients_df["Total Paid"].sum()
    total_due = clients_df["Total Due"].sum()
    paid_salaries = salaries_df.query("Paid=='Yes'")["Salary"].sum()
    unpaid_salaries = salaries_df.query("Paid=='No'")["Salary"].sum()
    total_expenses = expenses_df["Amount"].sum() + paid_salaries

    for c, (label, val) in zip(st.columns(5), [
        ("Income", total_income),
        ("Outstanding", total_due),
        ("Expenses", total_expenses),
        ("Paid Salaries", paid_salaries),
        ("Unpaid Salaries", unpaid_salaries)
    ]):
        c.metric(label, money(val))

elif page == "Clients & Projects":
    st.header("👥 Clients & Projects")
    if st.button("🔄 Reset Clients"):
        clients_df = pd.read_csv(FILES["clients"])
        st.rerun()
    clients_df = st.data_editor(clients_df, use_container_width=True, num_rows="dynamic", key="edit_clients")
    if st.button("💾 Save Clients"):
        save_df(clients_df, FILES["clients"])
        st.success("Clients updated.")

    st.subheader("📁 Projects")
    if st.button("🔄 Reset Projects"):
        projects_df = pd.read_csv(FILES["projects"])
        st.rerun()
    projects_df = st.data_editor(projects_df, use_container_width=True, num_rows="dynamic", key="edit_projects")
    if st.button("💾 Save Projects"):
        save_df(projects_df, FILES["projects"])
        st.success("Projects updated.")

elif page == "Employee Salaries":
    st.header("💼 Employee Salaries")
    if st.button("🔄 Reset Salaries"):
        salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"])
        st.rerun()
    salaries_df = st.data_editor(salaries_df, use_container_width=True, num_rows="dynamic", key="edit_salaries")
    if st.button("💾 Save Salaries"):
        save_df(salaries_df, FILES["salaries"])
        st.success("Salaries updated.")

elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    if st.button("🔄 Reset Expenses"):
        expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"])
        st.rerun()
    expenses_df = st.data_editor(expenses_df, use_container_width=True, num_rows="dynamic", key="edit_expenses")
    if st.button("💾 Save Expenses"):
        save_df(expenses_df, FILES["expenses"])
        st.success("Expenses updated.")

elif page == "Invoice Generator":
    st.header("🧾 Invoice Generator")
    if projects_df.empty:
        st.warning("No projects available.")
    else:
        client = st.selectbox("Client", projects_df["Client"].unique())
        filtered = projects_df[projects_df["Client"] == client]
        project = st.selectbox("Project", filtered["Project"].unique())
        selected = filtered[filtered["Project"] == project].iloc[0]

        milestone_label, amount = None, 0
        for milestone in ["Payment 20%", "Payment 40%", "Payment 40% (2)"]:
            if milestone in selected and pd.notnull(selected[milestone]) and selected[milestone] > 0:
                milestone_label = milestone
                amount = selected[milestone]
                break

        if milestone_label:
            st.write(f"Next payment due: **{milestone_label}** — ${amount:,.2f}")
            if st.button("Generate Invoice"):
                pdf = InvoicePDF()
                pdf.add_page()
                pdf.set_font("Helvetica", size=12)
                pdf.cell(0, 10, f"Invoice for {selected['Client']}: {milestone_label}", ln=True)
                pdf.cell(0, 10, f"Project: {selected['Project']} | Amount: ${amount:,.2f}", ln=True)
                fname = f"Invoice_{selected['Client'].replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf"
                fpath = INV_DIR / fname
                pdf.output(str(fpath))
                st.download_button("Download Invoice", open(fpath, "rb"), file_name=fname)
        else:
            st.success("✅ All payments completed.")

elif page == "Analytics":
    st.header("📊 Financial Charts")
    if not clients_df.empty:
        fig = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
        st.plotly_chart(fig, use_container_width=True)

    if not projects_df.empty:
        projects_df["Budget"] = pd.to_numeric(projects_df["Budget"], errors="coerce").fillna(0)
        milestone_sum = {
            "20%": projects_df["Payment 20%"].sum(),
            "40%": projects_df["Payment 40%"].sum(),
            "40% (2)": projects_df["Payment 40% (2)"].sum(),
        }
        fig2 = px.pie(values=list(milestone_sum.values()), names=list(milestone_sum.keys()), hole=0.4, title="Project Payment % Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    if not expenses_df.empty:
        exp_sum = expenses_df.groupby("Category")["Amount"].sum().reset_index()
        fig3 = px.pie(exp_sum, values="Amount", names="Category", title="Expenses by Category", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)

elif page == "Monthly Plans":
    st.header("📆 Monthly Payment Plans")
    if st.button("🔄 Reset Monthly Plans"):
        monthly_df = pd.read_csv(FILES["monthly"])
        st.rerun()
    monthly_df = st.data_editor(monthly_df, use_container_width=True, num_rows="dynamic", key="edit_monthly")
    if st.button("💾 Save Monthly Plans"):
        save_df(monthly_df, FILES["monthly"])
        st.success("Monthly plans updated.")

    unpaid = monthly_df[(monthly_df["Paid"] == "No") & (monthly_df["Month"] == date.today().strftime("%B %Y"))]
    if not unpaid.empty:
        st.subheader("🚨 Unpaid Clients")
        for i, row in unpaid.iterrows():
            with st.expander(f"{row['Client']} — ${row['Amount']:.2f}"):
                if st.button(f"📄 Generate Payment Request — {row['Client']}", key=f"invoice_{i}"):
                    pdf = InvoicePDF()
                    pdf.add_page()
                    pdf.monthly_invoice(row)
                    filename = f"MonthlyInvoice_{row['Client'].replace(' ', '_')}_{row['Month'].replace(' ', '_')}.pdf"
                    path = INV_DIR / filename
                    pdf.output(path.as_posix())
                    st.download_button("📥 Download PDF", open(path, "rb"), file_name=filename)
                    st.success("PDF Created")
