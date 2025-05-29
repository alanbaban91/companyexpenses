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
    "Expenses", "Invoice Generator", "Monthly Plans",
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

    st.markdown("---")
    st.subheader("📊 Financial Charts")

    chart_cols = st.columns(3)
    with chart_cols[0]:
        if not clients_df.empty:
            fig = px.bar(clients_df, x="Client", y="Total Paid", title="Client Payment Overview")
            st.plotly_chart(fig, use_container_width=True)

    with chart_cols[1]:
        if not projects_df.empty:
            projects_df["Budget"] = pd.to_numeric(projects_df["Budget"], errors="coerce").fillna(0)
            milestone_sum = {
                "20%": projects_df["Payment 20%"].sum(),
                "40%": projects_df["Payment 40%"].sum(),
                "40% (2)": projects_df["Payment 40% (2)"].sum(),
            }
            fig2 = px.pie(values=list(milestone_sum.values()), names=list(milestone_sum.keys()), hole=0.4, title="Project Payment % Distribution")
            st.plotly_chart(fig2, use_container_width=True)

    with chart_cols[2]:
        if not expenses_df.empty:
            exp_sum = expenses_df.groupby("Category")["Amount"].sum().reset_index()
            fig3 = px.pie(exp_sum, values="Amount", names="Category", title="Expenses by Category", hole=0.4)
            st.plotly_chart(fig3, use_container_width=True)

elif page == "Clients & Projects":
    st.header("👤 Clients")
    clients_df = st.data_editor(clients_df, num_rows="dynamic", use_container_width=True, key="clients")
    if st.button("💾 Save Clients"):
        save_df(clients_df, FILES["clients"])
        st.success("Clients saved.")

    st.markdown("---")
    st.header("📂 Projects")
    projects_df = st.data_editor(projects_df, num_rows="dynamic", use_container_width=True, key="projects")

    st.subheader("📈 Project Payment Progress")
    for idx, row in projects_df.iterrows():
        try:
            paid = sum([
                float(row.get("Payment 20%", 0) or 0),
                float(row.get("Payment 40%", 0) or 0),
                float(row.get("Payment 40% (2)", 0) or 0)
            ])
            budget = float(row.get("Budget", 0) or 0)
            progress = min(paid / budget, 1.0) if budget > 0 else 0.0
            st.markdown(f"**{row['Project']}** — {row['Client']}")
            st.progress(progress)
        except Exception as e:
            st.warning(f"Error processing project '{row['Project']}': {e}")

    p1, p2 = st.columns([1, 2])
    if p1.button("💾 Save Projects"):
        save_df(projects_df, FILES["projects"])
        st.success("Projects saved.")

    if p2.button("📦 Archive Projects"):
        try:
            mth_f = datetime.today().strftime("%B_%Y")
            archive_file = ARCHIVE_DIR / f"projects_{mth_f}.csv"
            if not projects_df.empty and all(col in projects_df.columns for col in COLUMNS["projects"]):
                projects_df.to_csv(archive_file, index=False)
                st.success("Projects archived.")
            else:
                st.warning("Projects not archived: file is empty or missing columns.")
        except Exception as err:
            st.error(f"Failed to archive projects: {err}")

elif page == "Employee Salaries":
    st.header("Employee Salaries")
    salaries_df = st.data_editor(salaries_df, num_rows="dynamic", use_container_width=True, key="edit_sal")
    if st.button("📂 Save Salaries"):
        save_df(salaries_df, FILES["salaries"])
        st.success("Salaries saved.")

elif page == "Expenses":
    st.header("💸 Monthly Expenses")
    expenses_df = st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, key="edit_exp")
    if st.button("📂 Save Expenses"):
        save_df(expenses_df, FILES["expenses"])
        st.success("Expenses saved.")

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

elif page == "Monthly Plans":
    st.header("📆 Monthly Payment Plans")
    monthly_df = st.data_editor(monthly_df, num_rows="dynamic", use_container_width=True, key="edit_month")
    if st.button("📂 Save Monthly Plans"):
        save_df(monthly_df, FILES["monthly"])
        st.success("Saved")

elif page == "🔄 Archive & Reset All":
    st.header("Start New Month")
    mth_f = datetime.today().strftime("%B_%Y")
    if st.button("Archive and Reset"):
        try:
            for key, path in FILES.items():
                if key == "projects":
                    continue  # Skip projects; handled separately

                archive_file = ARCHIVE_DIR / f"{key}_{mth_f}.csv"
                try:
                    df = pd.read_csv(path)
                    if not df.empty and all(col in df.columns for col in COLUMNS[key]):
                        df.to_csv(archive_file, index=False)
                    else:
                        st.warning(f"Skipped archiving {key}: file is empty or missing expected columns.")
                except Exception as read_err:
                    st.error(f"Error reading {key}: {read_err}")
                    continue

                pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

            st.success("Archived & reset (excluding projects).")
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
                if "DueDate" in df.columns:
            st.markdown("---")
            st.subheader("📅 Upcoming Payments from Archive")
            try:
                df["DueDate"] = pd.to_datetime(df["DueDate"], errors="coerce")
                upcoming = df[(df["Paid"] != "Yes") & (df["DueDate"] >= datetime.today()) & (df["DueDate"] <= datetime.today() + timedelta(days=7))]
                if not upcoming.empty:
                    for _, row in upcoming.iterrows():
                        due_in_days = (row["DueDate"] - datetime.today()).days
                        urgency = "🔴 Urgent" if due_in_days <= 2 else "🟠 Soon"
                        st.markdown(f"**{row['Client']}** — {money(row['Amount'])} via {row['Payment Method']} ({urgency})")
                        st.info(f"Archived Reminder: {row['Client']} owes {money(row['Amount'])} due on {row['DueDate'].strftime('%Y-%m-%d')}")
                else:
                    st.info("✅ No upcoming payments in this archive.")
            except Exception as e:
                st.error(f"Failed to parse due dates in archive: {e}")

