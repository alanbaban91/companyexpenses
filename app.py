from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import pandas as pd
import streamlit as st
import plotly.express as px
from fpdf import FPDF
import hashlib

# ──────────────────── Paths & Setup ────────────────────
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
    "users": DATA_DIR / "users.csv"
}

COLUMNS: Dict[str, List[str]] = {
    "clients":  ["Client", "Contact", "Total Paid", "Total Due"],
    "projects": ["Client", "Project", "Employee", "Budget", "Payment 20%", "Payment 40%", "Payment 40% (2)", "Paid Status"],
    "salaries": ["Employee", "Role", "Salary", "Paid", "Date"],
    "expenses": ["Category", "Amount", "Date", "Notes"],
    "monthly":  ["Client", "Amount", "Payment Method", "Social Media Budget", "Paid", "Month", "DueDate"],
    "users": ["Username", "Password", "Role"]
}

for key, path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path, index=False)

# ──────────────────── Authentication ────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    users_df = pd.read_csv(FILES["users"])
    if username in users_df["Username"].values:
        record = users_df[users_df["Username"] == username].iloc[0]
        if record["Password"] == hash_password(password):
            return True, record["Role"]
    return False, None

st.set_page_config("33Studio Finance Dashboard", layout="wide")

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.last_active = datetime.now()

if not st.session_state.auth:
    with st.form("Login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            ok, role = check_credentials(user, pwd)
            if ok:
                st.session_state.auth = True
                st.session_state.role = role
                st.session_state.username = user
                st.session_state.last_active = datetime.now()
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

if datetime.now() - st.session_state.last_active > timedelta(minutes=15):
    st.session_state.auth = False
    st.experimental_rerun()
else:
    st.session_state.last_active = datetime.now()

if st.button("🔒 Logout"):
    st.session_state.auth = False
    st.experimental_rerun()

# ───────────────────── Load Data ─────────────────────
clients_df = pd.read_csv(FILES["clients"])
projects_df = pd.read_csv(FILES["projects"])
salaries_df = pd.read_csv(FILES["salaries"], parse_dates=["Date"], dayfirst=True)
expenses_df = pd.read_csv(FILES["expenses"], parse_dates=["Date"], dayfirst=True)
monthly_df = pd.read_csv(FILES["monthly"], parse_dates=["DueDate"], dayfirst=True)
users_df = pd.read_csv(FILES["users"])

# ───────────────────── Helpers ─────────────────────
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

# ───────────────────── UI Pages ─────────────────────
pages = ["Dashboard", "Clients", "Projects", "Salaries", "Expenses", "Monthly Plans", "Invoice Generator", "View Archives"]
if st.session_state.role == "admin":
    pages.append("Admin Panel")
page = st.sidebar.radio("Navigate", pages)

if page == "Dashboard":
    st.header("📊 Dashboard Overview")
    inc = clients_df["Total Paid"].fillna(0).sum()
    out = clients_df["Total Due"].fillna(0).sum()
    paid_sal = salaries_df[salaries_df["Paid"] == "Yes"]["Salary"].sum()
    exp = expenses_df["Amount"].sum() + paid_sal

    cols = st.columns(4)
    cols[0].metric("Income", money(inc))
    cols[1].metric("Outstanding", money(out))
    cols[2].metric("Paid Salaries", money(paid_sal))
    cols[3].metric("Expenses", money(exp))

    st.markdown("---")
    st.subheader("📅 Upcoming Payments")
    upcoming = monthly_df[(monthly_df["Paid"] != "Yes") & (monthly_df["DueDate"] >= datetime.today()) & (monthly_df["DueDate"] <= datetime.today() + timedelta(days=7))]
    if not upcoming.empty:
        for _, row in upcoming.iterrows():
            due_days = (row["DueDate"] - datetime.today()).days
            urgency = "🔴 Urgent" if due_days <= 2 else "🟠 Soon"
            st.markdown(f"**{row['Client']}** — {money(row['Amount'])} ({urgency}) due {row['DueDate'].strftime('%Y-%m-%d')}")
    else:
        st.info("✅ No upcoming payments.")

if page == "Clients":
    st.header("👤 Clients")
    st.data_editor(clients_df, num_rows="dynamic", use_container_width=True, key="edit_clients")
    if st.button("💾 Save Clients"):
        save_df(clients_df, FILES["clients"])
        st.success("Saved.")

if page == "Projects":
    st.header("📂 Projects")
    st.data_editor(projects_df, num_rows="dynamic", use_container_width=True, key="edit_projects")
    if st.button("💾 Save Projects"):
        save_df(projects_df, FILES["projects"])
        st.success("Saved.")

if page == "Salaries":
    st.header("👥 Employee Salaries")
    st.data_editor(salaries_df, num_rows="dynamic", use_container_width=True, key="edit_salaries")
    if st.button("💾 Save Salaries"):
        save_df(salaries_df, FILES["salaries"])
        st.success("Saved.")

if page == "Expenses":
    st.header("💸 Expenses")
    st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, key="edit_expenses")
    if st.button("💾 Save Expenses"):
        save_df(expenses_df, FILES["expenses"])
        st.success("Saved.")

if page == "Monthly Plans":
    st.header("📆 Monthly Plans")
    st.data_editor(monthly_df, num_rows="dynamic", use_container_width=True, key="edit_month")
    if st.button("💾 Save Monthly"):
        save_df(monthly_df, FILES["monthly"])
        st.success("Saved.")

if page == "Invoice Generator":
    st.header("🧾 Generate Invoice")
    if projects_df.empty:
        st.warning("No project data available.")
    else:
        client = st.selectbox("Client", projects_df["Client"].unique())
        filtered = projects_df[projects_df["Client"] == client]
        project = st.selectbox("Project", filtered["Project"].unique())
        selected = filtered[filtered["Project"] == project].iloc[0]
        for label in ["Payment 20%", "Payment 40%", "Payment 40% (2)"]:
            if pd.notnull(selected[label]) and selected[label] > 0:
                st.write(f"Next Milestone: **{label}** — {money(selected[label])}")
                if st.button("Generate Invoice"):
                    pdf = InvoicePDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell_safe(0, 10, f"Invoice for {selected['Client']}: {label}", ln=True)
                    pdf.cell_safe(0, 10, f"Project: {selected['Project']} | Amount: {money(selected[label])}", ln=True)
                    fname = f"Invoice_{selected['Client'].replace(' ', '_')}_{datetime.now():%Y%m%d}.pdf"
                    fpath = INV_DIR / fname
                    pdf.output(str(fpath))
                    st.download_button("Download Invoice", open(fpath, "rb"), file_name=fname)
                break

if page == "View Archives":
    st.header("📁 View Archives")
    files = sorted(ARCHIVE_DIR.glob("*.csv"), reverse=True)
    selected = st.selectbox("Select Archive File", [f.name for f in files])
    if selected:
        df = pd.read_csv(ARCHIVE_DIR / selected)
        st.dataframe(df, use_container_width=True)

if page == "Admin Panel" and st.session_state.role == "admin":
    st.header("🔐 Admin Panel")
    st.dataframe(users_df.drop(columns=["Password"]))
    new_user = st.text_input("New Username")
    new_pwd = st.text_input("New Password", type="password")
    new_role = st.selectbox("Role", ["admin", "viewer"])
    if st.button("Add User"):
        if new_user and new_pwd:
            new_entry = pd.DataFrame([[new_user, hash_password(new_pwd), new_role]], columns=COLUMNS["users"])
            users_df = pd.concat([users_df, new_entry], ignore_index=True)
            save_df(users_df, FILES["users"])
            st.success("User added.")
    del_user = st.text_input("Delete Username")
    if st.button("Delete User"):
        users_df = users_df[users_df["Username"] != del_user]
        save_df(users_df, FILES["users"])
        st.warning("User deleted.")
