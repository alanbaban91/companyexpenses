from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF

# ───────────────────── Paths & Setup ─────────────────────
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

COLUMNS: Dict[str, List[str]] = {
    "clients":  ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "monthly":  ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month"],
}

for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

clients_df  = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"], dayfirst=True)
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"], dayfirst=True)
monthly_df  = pd.read_csv(FILES["monthly"])

st.set_page_config("33Studio Finance Dashboard", layout="wide")
st.title("33Studio Finance Dashboard")

if hasattr(st, "rerun"):
    _rerun = st.rerun
elif hasattr(st, "experimental_rerun"):
    _rerun = st.experimental_rerun
else:
    def _rerun():
        raise RuntimeError("Please refresh the page to see updates.")

pages = [
    "Dashboard", "Clients & Projects", "Employee Salaries",
    "Expenses", "Invoice Generator", "Analytics", "Monthly Plans",
    "🔄 Archive & Reset All", "📁 View Archives"
]
page = st.sidebar.radio("Navigate", pages)

# Helpers
def save_df(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)

def money(x: float) -> str:
    return f"${x:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Invoice", ln=True, align="C")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    def cell_safe(self, w, h, txt, **kwargs):
        safe = txt.encode("latin-1", "replace").decode("latin-1")
        self.cell(w, h, safe, **kwargs)

# ───────────────────── Pages ─────────────────────
if page == "Dashboard":
    st.header("Overview Metrics")
    clients_df[["Total Paid", "Total Due"]] = clients_df[["Total Paid", "Total Due"]].apply(pd.to_numeric, errors="coerce").fillna(0)
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
    clients_df = st.data_editor(clients_df, num_rows="dynamic", use_container_width=True, key="clients")
    if st.button("💾 Save Clients"):
        save_df(clients_df, FILES["clients"])
        st.success("Saved")

    st.subheader("📂 Projects")
    projects_df = st.data_editor(projects_df, num_rows="dynamic", use_container_width=True, key="projects")
    if st.button("💾 Save Projects"):
        save_df(projects_df, FILES["projects"])
        st.success("Saved")

elif page == "Employee Salaries":
    st.header("Employee Salaries")
    salaries_df = st.data_editor(salaries_df, num_rows="dynamic", use_container_width=True, key="edit_sal")
    if st.button("💾 Save Salaries"):
        save_df(salaries_df, FILES["salaries"])
        st.success("Saved")

elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    expenses_df = st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, key="edit_exp")
    if st.button("💾 Save Expenses"):
        save_df(expenses_df, FILES["expenses"])
        st.success("Saved")

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
                pdf.set_font("Arial", size=12)
                pdf.cell_safe(0, 10, f"Invoice for {selected['Client']}: {milestone_label}", ln=True)
                pdf.cell_safe(0, 10, f"Project: {selected['Project']} | Amount: ${amount:,.2f}", ln=True)
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
    monthly_df = st.data_editor(monthly_df, num_rows="dynamic", use_container_width=True, key="edit_month")
    if st.button("💾 Save Monthly Plans"):
        save_df(monthly_df, FILES["monthly"])
        st.success("Saved")

elif page == "🔄 Archive & Reset All":
    st.header("Start New Month")
    mth_f = datetime.today().strftime("%B_%Y")
    if st.button("Archive and Reset"):
        try:
            for key, path in FILES.items():
                archive_file = ARCHIVE_DIR / f"{key}_{mth_f}.csv"

                # Try reading the existing file
                try:
                    df = pd.read_csv(path)
                    if not df.empty and all(col in df.columns for col in COLUMNS[key]):
                        df.to_csv(archive_file, index=False)
                    else:
                        st.warning(f"Skipped archiving {key}: file is empty or missing expected columns.")
                except Exception as read_err:
                    st.error(f"Error reading {key}: {read_err}")
                    continue

                # Reset the file to empty with proper headers
                pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

            st.success("Archived & reset.")
            _rerun()

        except Exception as err:
            st.error(f"Unexpected error during archive/reset: {err}")

elif page == "📁 View Archives":
    st.header("📁 Archived Reports")
    files = sorted(ARCHIVE_DIR.glob("*.csv"), reverse=True)
    selected = st.selectbox("Select Archive File", [f.name for f in files])
    if selected:
        df = pd.read_csv(ARCHIVE_DIR / selected)
        st.dataframe(df, use_container_width=True)
