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
DATA_DIR = BASE_DIR / 'data'
ARCHIVE_DIR = BASE_DIR / 'archive'
INV_DIR = BASE_DIR / 'invoices'
for d in (DATA_DIR, ARCHIVE_DIR, INV_DIR):
    d.mkdir(exist_ok=True)

FILES: Dict[str, Path] = {
    'clients': DATA_DIR / 'clients.csv',
    'projects': DATA_DIR / 'projects.csv',
    'salaries': DATA_DIR / 'salaries.csv',
    'expenses': DATA_DIR / 'expenses.csv',
    'monthly': DATA_DIR / 'monthly.csv',
    'users': DATA_DIR / 'users.csv',
}

COLUMNS: Dict[str, List[str]] = {
    'clients': ['Client', 'Contact', 'Total Paid', 'Total Due'],
    'projects': ['Client','Project','Employee','Budget','Payment 20%','Payment 40%','Payment 40% (2)','Paid Status'],
    'salaries': ['Employee','Role','Salary','Paid','Date'],
    'expenses': ['Category','Amount','Date','Notes'],
    'monthly': ['Client','Amount','Payment Method','Social Media Budget','Paid','Month','DueDate'],
    'users': ['Username','Password','Role'],
}

# Ensure CSVs exist
for key,path in FILES.items():
    if not path.exists():
        pd.DataFrame(columns=COLUMNS[key]).to_csv(path,index=False)

# ──────────────────── Authentication ────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str) -> tuple[bool,str|None]:
    df = pd.read_csv(FILES['users'])
    if username in df['Username'].values:
        rec = df[df['Username']==username].iloc[0]
        if rec['Password']==hash_password(password):
            return True,rec['Role']
    return False,None

# ──────────────────── App Config & Session ────────────────────
st.set_page_config('33Studio Finance Dashboard',layout='wide')
if 'auth' not in st.session_state:
    st.session_state.auth=False
    st.session_state.role=None
    st.session_state.username=''
    st.session_state.last_active=datetime.now()

# ──────────────────── Login ────────────────────
if not st.session_state.auth:
    with st.form('Login'):
        user=st.text_input('Username')
        pwd=st.text_input('Password',type='password')
        if st.form_submit_button('Login'):
            ok,role=check_credentials(user,pwd)
            if ok:
                st.session_state.auth=True
                st.session_state.role=role
                st.session_state.username=user
                st.session_state.last_active=datetime.now()
                st.rerun()
            else:
                st.error('Invalid credentials')
    st.stop()

# ──────────────────── Top Bar (Logout) ────────────────────
logout_col1,logout_col2 = st.columns([0.85,0.15])
with logout_col2:
    if st.button('🔒 Logout'):
        st.session_state.auth=False
        st.rerun()

# Auto-logout after inactivity
if datetime.now()-st.session_state.last_active>timedelta(minutes=15):
    st.session_state.auth=False
    st.rerun()
else:
    st.session_state.last_active=datetime.now()

# ───────────────────── Load Data ─────────────────────
clients_df=pd.read_csv(FILES['clients'])
projects_df=pd.read_csv(FILES['projects'])
salaries_df=pd.read_csv(FILES['salaries'],parse_dates=['Date'],dayfirst=True)
expenses_df=pd.read_csv(FILES['expenses'],parse_dates=['Date'],dayfirst=True)
monthly_df=pd.read_csv(FILES['monthly'])
if 'DueDate' in monthly_df.columns:
    monthly_df['DueDate']=pd.to_datetime(monthly_df['DueDate'],errors='coerce',dayfirst=True)
elif 'Month' in monthly_df.columns:
    monthly_df['DueDate']=pd.to_datetime(monthly_df['Month'],errors='coerce',dayfirst=True)
else:
    monthly_df['DueDate']=pd.NaT
users_df=pd.read_csv(FILES['users'])

# ───────────────────── Helpers ─────────────────────
def save_df(df:pd.DataFrame,path:Path)->None:
    df.to_csv(path,index=False)

def money(x:float)->str:
    return f"${x:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        self.set_font('Arial','B',14)
        self.cell(0,10,'Invoice',ln=True,align='C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial','I',8)
        self.cell(0,10,f'Page {self.page_no()}',align='C')
    def cell_safe(self,w:float,h:float,txt:str,**kwargs)->None:
        safe=txt.encode('latin-1','replace').decode('latin-1')
        self.cell(w,h,safe,**kwargs)

# ───────────────────── Navigation ─────────────────────
pages=['Dashboard','Clients','Projects','Salaries','Expenses','Monthly Plans','Invoice Generator','View Archives']
if st.session_state.role=='admin': pages.append('Admin Panel')
page=st.sidebar.radio('Navigate',pages)

# ───────────────────── Pages ─────────────────────
if page=='Dashboard':
    st.header('📊 Dashboard Overview')
    inc=clients_df['Total Paid'].apply(pd.to_numeric,errors='coerce').fillna(0).sum()
    out=clients_df['Total Due'].apply(pd.to_numeric,errors='coerce').fillna(0).sum()
    paid_sal=salaries_df[salaries_df['Paid']=='Yes']['Salary'].sum()
    exp_tot=expenses_df['Amount'].sum()+paid_sal
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Income',money(inc))
    c2.metric('Outstanding',money(out))
    c3.metric('Paid Salaries',money(paid_sal))
    c4.metric('Expenses',money(exp_tot))
    st.markdown('---')
    # Monthly payment reminders
    st.subheader('📅 Upcoming Monthly Payments')
    upcoming=monthly_df[(monthly_df['Paid']!='Yes')&(monthly_df['DueDate']>=datetime.today())&(monthly_df['DueDate']<=datetime.today()+timedelta(days=7))]
    if not upcoming.empty:
        for _,r in upcoming.iterrows():
            d=(r['DueDate']-datetime.today()).days
            u='🔴 Urgent' if d<=2 else '🟠 Soon'
            st.markdown(f"**{r['Client']}** — {money(r['Amount'])} ({u}) due {r['DueDate'].strftime('%Y-%m-%d')}")
    else: st.info('✅ No upcoming monthly payments.')
    # Project milestone reminders
    st.markdown('---')
    st.subheader('📂 Upcoming Project Payments')
    project_reminders=[]
    for _,row in projects_df.iterrows():
        if str(row.get('Paid Status','')).lower()=='yes': continue
        for lbl in ['Payment 20%','Payment 40%','Payment 40% (2)']:
            try: amt=float(row.get(lbl,0))
            except: amt=0
            if amt>0:
                project_reminders.append((row['Client'],row['Project'],lbl,amt))
    if project_reminders:
        for client,proj,lbl,amt in project_reminders:
            st.markdown(f"**{client} - {proj}** — {lbl}: {money(amt)} (Due now)")
    else: st.info('✅ No upcoming project payments.')

elif page=='Clients':
    st.header('👤 Clients')
    clients_df = st.data_editor(clients_df, num_rows='dynamic', use_container_width=True, key='edit_clients')
    if st.button('💾 Save Clients'):
        save_df(clients_df, FILES['clients'])
        st.success('Clients saved.')

    # ─────── Client Payment Breakdown Chart ───────
    st.subheader('💹 Client Payment Breakdown')
    chart_df = clients_df.copy()
    chart_df[["Total Paid", "Total Due"]] = chart_df[["Total Paid", "Total Due"]].apply(pd.to_numeric, errors='coerce').fillna(0)
    if not chart_df.empty:
        fig = px.bar(chart_df, x='Client', y=['Total Paid', 'Total Due'], barmode='group', title='Total Paid vs. Total Due by Client')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('No client data to display.')

elif page=='Projects':
    st.header('📂 Projects')
    projects_df = st.data_editor(projects_df, num_rows='dynamic', use_container_width=True, key='edit_projects')

    # Buttons side‑by‑side
    btn_save, btn_archive, _ = st.columns([1,1,6])
    with btn_save:
        if st.button('💾 Save Projects'):
            save_df(projects_df, FILES['projects'])
            st.success('Projects saved.')

    with btn_archive:
        if st.button('📦 Archive Projects'):
            m = datetime.today().strftime('%B_%Y')
            projects_df.to_csv(ARCHIVE_DIR / f'projects_{m}.csv', index=False)
            st.success('Projects archived.')

    # ─────── Add New Project Form ───────
    with st.expander('➕ Add New Project'):
        n_client = st.text_input('Client', key='np_client')
        n_project = st.text_input('Project', key='np_project')
        n_employee = st.text_input('Employee', key='np_emp')
        n_budget = st.number_input('Budget', min_value=0.0, step=100.0, key='np_budget')
        n_p20 = st.number_input('Payment 20%', min_value=0.0, step=50.0, key='np_p20')
        n_p40 = st.number_input('Payment 40%', min_value=0.0, step=50.0, key='np_p40')
        n_p40_2 = st.number_input('Payment 40% (2)', min_value=0.0, step=50.0, key='np_p40_2')
        n_paid = st.selectbox('Paid Status', ['No', 'Yes'], key='np_paid')
        if st.button('Add Project'):
            new_row = {
                'Client': n_client,
                'Project': n_project,
                'Employee': n_employee,
                'Budget': n_budget,
                'Payment 20%': n_p20,
                'Payment 40%': n_p40,
                'Payment 40% (2)': n_p40_2,
                'Paid Status': n_paid
            }
            projects_df = pd.concat([projects_df, pd.DataFrame([new_row])], ignore_index=True)
            save_df(projects_df, FILES['projects'])
            st.success('New project added.')
            st.rerun()

elif page=='Salaries':
    st.header('💼 Employee Salaries')
    salaries_df = st.data_editor(salaries_df, num_rows='dynamic', use_container_width=True, key='edit_salaries')

    # Buttons side‑by‑side
    btn_save_sal, btn_arch_sal, _ = st.columns([1, 1, 6])
    with btn_save_sal:
        if st.button('💾 Save Salaries'):
            save_df(salaries_df, FILES['salaries'])
            st.success('Salaries saved.')
    with btn_arch_sal:
        if st.button('📦 Archive Salaries'):
            m = datetime.today().strftime('%B_%Y')
            salaries_df.to_csv(ARCHIVE_DIR / f'salaries_{m}.csv', index=False)
            st.success('Salaries archived.')

    # ─────── Add New Salary Record ───────
    with st.expander('➕ Add Salary Payment'):
        e_name = st.text_input('Employee Name', key='ns_emp')
        e_role = st.text_input('Role / Position', key='ns_role')
        e_salary = st.number_input('Salary Amount', min_value=0.0, step=50.0, key='ns_amount')
        e_paid = st.selectbox('Paid', ['No', 'Yes'], key='ns_paid')
        e_date = st.date_input('Payment Date', value=datetime.today(), key='ns_date')
        if st.button('Add Salary Record'):
            new_sal = {
                'Employee': e_name,
                'Role': e_role,
                'Salary': e_salary,
                'Paid': e_paid,
                'Date': pd.to_datetime(e_date)
            }
            salaries_df = pd.concat([salaries_df, pd.DataFrame([new_sal])], ignore_index=True)
            save_df(salaries_df, FILES['salaries'])
            st.success('New salary record added.')
            st.rerun()

elif page=='Expenses':
    st.header('💸 Expenses')
    expenses_df = st.data_editor(expenses_df, num_rows='dynamic', use_container_width=True, key='edit_expenses')

    # Buttons side‑by‑side
    btn_save_exp, btn_arch_exp, _ = st.columns([1, 1, 6])
    with btn_save_exp:
        if st.button('💾 Save Expenses'):
            save_df(expenses_df, FILES['expenses'])
            st.success('Expenses saved.')
    with btn_arch_exp:
        if st.button('📦 Archive Expenses'):
            m = datetime.today().strftime('%B_%Y')
            expenses_df.to_csv(ARCHIVE_DIR / f'expenses_{m}.csv', index=False)
            st.success('Expenses archived.')

    # ─────── Add New Expense ───────
    with st.expander('➕ Add Expense'):
        ex_cat = st.text_input('Category', key='ne_cat')
        ex_amt = st.number_input('Amount', min_value=0.0, step=1.0, key='ne_amt')
        ex_date = st.date_input('Date', value=datetime.today(), key='ne_date')
        ex_notes = st.text_input('Notes', key='ne_notes')
        if st.button('Add Expense'):
            new_exp = {
                'Category': ex_cat,
                'Amount': ex_amt,
                'Date': pd.to_datetime(ex_date),
                'Notes': ex_notes
            }
            expenses_df = pd.concat([expenses_df, pd.DataFrame([new_exp])], ignore_index=True)
            save_df(expenses_df, FILES['expenses'])
            st.success('New expense added.')
            st.rerun()

elif page=='Monthly Plans':
    st.header('📆 Monthly Plans')
    monthly_df = st.data_editor(monthly_df, num_rows='dynamic', use_container_width=True, key='edit_monthly')

    # Buttons side‑by‑side
    btn_save_mp, btn_arch_mp, _ = st.columns([1, 1, 8])
    with btn_save_mp:
        if st.button('💾 Save Monthly Plans'):
            save_df(monthly_df, FILES['monthly'])
            st.success('Monthly plans saved.')
    with btn_arch_mp:
        if st.button('📦 Archive Monthly'):
            m = datetime.today().strftime('%B_%Y')
            monthly_df.to_csv(ARCHIVE_DIR / f'monthly_{m}.csv', index=False)
            st.success('Monthly plans archived.')

    # ─────── Add Monthly Plan ───────
    with st.expander('➕ Add Monthly Plan'):
        mp_client = st.text_input('Client', key='nm_client')
        mp_amt = st.number_input('Amount', min_value=0.0, step=50.0, key='nm_amt')
        mp_method = st.text_input('Payment Method', key='nm_method')
        mp_social = st.number_input('Social Media Budget', min_value=0.0, step=10.0, key='nm_social')
        mp_paid = st.selectbox('Paid', ['No', 'Yes'], key='nm_paid')
        mp_month = st.date_input('Month', value=datetime.today(), key='nm_month')
        mp_due = st.date_input('Due Date', value=datetime.today()+timedelta(days=30), key='nm_due')
        if st.button('Add Monthly Plan'):
            new_mp = {
                'Client': mp_client,
                'Amount': mp_amt,
                'Payment Method': mp_method,
                'Social Media Budget': mp_social,
                'Paid': mp_paid,
                'Month': mp_month.strftime('%Y-%m'),
                'DueDate': pd.to_datetime(mp_due)
            }
            monthly_df = pd.concat([monthly_df, pd.DataFrame([new_mp])], ignore_index=True)
            save_df(monthly_df, FILES['monthly'])
            st.success('Monthly plan added.')
            st.rerun()

elif page=='Invoice Generator':
    st.header('📆 Monthly Plans')
    monthly_df=st.data_editor(monthly_df,num_rows='dynamic',use_container_width=True,key='edit_monthly')
    if st.button('💾 Save Monthly Plans'):
        save_df(monthly_df,FILES['monthly'])
        st.success('Monthly plans saved.')

elif page=='Invoice Generator':
    st.header('🧾 Generate Invoice')
    if projects_df.empty:
        st.warning('No projects available.')
    else:
        client=st.selectbox('Client',projects_df['Client'].unique())
        subset=projects_df[projects_df['Client']==client]
        project=st.selectbox('Project',subset['Project'].unique())
        sel=subset[subset['Project']==project].iloc[0]
        for lbl in ['Payment 20%','Payment 40%','Payment 40% (2)']:
            if pd.notnull(sel[lbl]) and sel[lbl]>0:
                st.write(f"Next Milestone: **{lbl}** — {money(sel[lbl])}")
                if st.button('Generate Invoice'):
                    pdf=InvoicePDF()
                    pdf.add_page()
                    pdf.set_font('Arial',size=12)
                    pdf.cell_safe(0,10,f"Invoice for {sel['Client']}: {lbl}",ln=True)
                    pdf.cell_safe(0,10,f"Project: {sel['Project']} | Amount: {money(sel[lbl])}",ln=True)
                    fn=f"Invoice_{sel['Client'].replace(' ','_')}_{datetime.now():%Y%m%d}.pdf"
                    fp=INV_DIR/fn
                    pdf.output(str(fp))
                    st.download_button('Download Invoice',open(fp,'rb'),file_name=fn)
                break

elif page=='View Archives':
    st.header('📁 View Archives')
    files=sorted(ARCHIVE_DIR.glob('*.csv'),reverse=True)
    sel=st.selectbox('Select Archive File',[f.name for f in files])
    if sel: dfar=pd.read_csv(ARCHIVE_DIR/sel);st.dataframe(dfar,use_container_width=True)

elif page=='Admin Panel' and st.session_state.role=='admin':
    st.header('🔐 Admin Panel')
    users_df=st.data_editor(users_df,num_rows='dynamic',use_container_width=True,key='edit_users')
    if st.button('💾 Save Users'):
        users_df['Password']=users_df['Password'].apply(lambda p: hash_password(p) if len(p)!=64 else p)
        save_df(users_df,FILES['users']);st.success('Users updated.')
