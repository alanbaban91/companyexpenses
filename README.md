companyExpenses

A Streamlit web application for managing all aspects of a small studio's finances, from clients and projects to salaries, expenses, and invoicing.

🚀 Features

User Authentication & Roles

Secure login with SHA-256 password hashing

Role-based access: admin vs viewer

Auto-logout after 15 minutes of inactivity

Dashboard

Key metrics: income, outstanding, paid salaries, expenses

Upcoming payment reminders with urgency color codes (🔴 Urgent / 🟠 Soon)

Clients & Projects

Dynamic data editor for clients and projects

Save and archive functionality (projects can be archived independently)

Progress tracker for project payment milestones

Employee Salaries & Expenses

Track salary payments and general expenses

Editable tables with save buttons

Monthly Plans

Plan future payments, set due dates, and view reminders

Invoice Generator

Generate milestone-based PDF invoices and download

Archives Viewer

Browse and view historical CSV snapshots

Admin Panel (admin only)

Create, edit, and delete users

Assign roles and manage credentials

🗂️ Repository Structure

  companyexpenses/
  ├── .devcontainer/          # Development container configuration
  ├── data/                   # CSV data files (clients, projects, salaries...)
  │   ├── clients.csv
  │   ├── projects.csv
  │   ├── salaries.csv
  │   ├── expenses.csv
  │   ├── monthly.csv
  │   └── users.csv           # User credentials and roles
  ├── archive/                # Archived CSV snapshots by month
  ├── invoices/               # Generated invoice PDFs
  ├── app.py                  # Main Streamlit application
  ├── README.md               # This documentation file
  └── requirements.txt        # Python dependencies

⚙️ Installation & Setup

Clone the repository

git clone https://github.com/<your-username>/companyexpenses.git
cd companyexpenses

Create & activate a virtual environment

python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate     # Windows

Install dependencies

pip install -r requirements.txt

Initialize data directory
The app.py script will automatically create the data/, archive/, and invoices/ folders on first run.

Create an initial admin user
Manually add to data/users.csv:

Username,Password,Role
admin,5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8,admin

The above password hash corresponds to password using SHA-256.

Run the app

streamlit run app.py


📈 Usage

Navigate between pages using the sidebar

Dashboard shows key metrics and upcoming reminders

Clients, Projects, Salaries, Expenses, Monthly Plans pages use editable tables

Invoice Generator creates PDF invoices for project milestones

View Archives lets you inspect past CSV snapshots

Admin Panel (admins only) to manage user accounts

💡 Customization

Adjust column schema in the COLUMNS dictionary at the top of app.py

Modify auto-logout timeout by changing 15 in timedelta(minutes=15)

Update styling or layout via Streamlit theming in ~/.streamlit/config.toml

📦 Deployment

Deploy easily on Streamlit Cloud or your own server:

streamlit run app.py --server.port 80

Use Docker by creating a Dockerfile based on the .devcontainer setup

Developed by alanbaban91

