import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import pandas as pd
from datetime import date

# --- Page Configuration ---
st.set_page_config(page_title="ContractOS", page_icon="🔒", layout="wide")

# --- Session State Initialization ---
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "password" not in st.session_state:
    st.session_state["password"] = ""

# --- Constants ---
SHEET_ID = '1QsIKLchwTzC0tAhdgT3JE6TFYRqWS-g5ZNyV5HYglCY'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')

# --- Helper Functions ---
def get_db_connection():
    """Establishes connection to Google Sheets with Secrets or Local Fallback."""
    creds = None
    
    # 1. Try Streamlit Secrets
    if 'gcp_service_account' in st.secrets:
        try:
            creds_dict = st.secrets['gcp_service_account']
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except Exception as e:
            st.error(f"Error loading secrets: {e}")

    # 2. Fallback to Local File
    if not creds and os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            st.error(f"Error loading local credentials: {e}")

    if not creds:
        st.error("No credentials found! Please set up st.secrets or credentials.json.")
        return None

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def init_sheet(sheet):
    """Ensures the necessary worksheets and headers exist."""
    if not sheet:
        return

    tables = {
        'Directory': ['Name', 'Company', 'Email', 'Phone', 'Address'],
        'Hours': ['Employee', 'Date', 'Hours', 'Task'],
        'Expenses': ['Category', 'Amount', 'Date', 'Description'],
        'Mileage': ['Date', 'License', 'Vehicle', 'Vehicle Type', 'Starting Odometer', 'Ending Odometer', 'Total Miles', 'Reimbursement Amount']
    }

    for name, headers in tables.items():
        try:
            worksheet = sheet.worksheet(name)
            # Check if empty and add headers if needed
            if not worksheet.row_values(1):
                worksheet.append_row(headers)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=name, rows=100, cols=20)
            worksheet.append_row(headers)

# --- Authentication ---
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Use .get() to avoid KeyError if keys are missing
        user = st.session_state.get("username", "")
        pw = st.session_state.get("password", "")
        
        if user == "admin" and pw == "battlebound2025":
            st.session_state["password_correct"] = True
            # Clear inputs
            st.session_state["username"] = "" 
            st.session_state["password"] = ""
        else:
            st.session_state["password_correct"] = False

    # Initialize state if not present
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # Show Login Form
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        
        # Show error only if they tried to log in and failed
        if st.session_state.get("password_correct") is False:
             # Only show error if they actually typed something (avoid error on first load)
            if st.session_state.get("username") or st.session_state.get("password"):
                st.error("😕 User not known or password incorrect")
        return False
    
    return True

# --- Main App Logic ---
if check_password():
    # Initialize Sheet
    sheet = get_db_connection()
    if sheet:
        init_sheet(sheet)

    st.sidebar.title("ContractOS 🚀")
    page = st.sidebar.radio("Navigate", ["Directory", "Hours", "Expenses", "Mileage"])
    
    if st.sidebar.button("Logout"):
        st.session_state["password_correct"] = False
        st.rerun()

    # --- Directory Page ---
    if page == "Directory":
        st.title("👥 Directory")
        
        with st.form("directory_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name")
            company = col2.text_input("Company")
            email = col1.text_input("Email")
            phone = col2.text_input("Phone")
            address = st.text_area("Address")
            
            submitted = st.form_submit_button("Save Contact")
            if submitted and name:
                if sheet:
                    ws = sheet.worksheet('Directory')
                    ws.append_row([name, company, email, phone, address])
                    st.success("Contact Saved!")
                else:
                    st.warning("Saved locally (No DB connection)")

        # Show Data
        if sheet:
            try:
                ws = sheet.worksheet('Directory')
                data = ws.get_all_records()
                if data:
                    st.dataframe(pd.DataFrame(data))
                else:
                    st.info("No contacts found.")
            except Exception as e:
                st.error(f"Error fetching data: {e}")

    # --- Hours Page ---
    elif page == "Hours":
        st.title("⏱️ Hour Tracker")
        
        with st.form("hours_form", clear_on_submit=True):
            employee = st.text_input("Employee Name")
            col1, col2 = st.columns(2)
            work_date = col1.date_input("Date", date.today())
            hours = col2.number_input("Hours Worked", step=0.5)
            task = st.text_area("Task / Description")
            
            submitted = st.form_submit_button("Log Hours")
            if submitted and employee:
                if sheet:
                    ws = sheet.worksheet('Hours')
                    ws.append_row([employee, str(work_date), hours, task])
                    st.success("Hours Logged!")

    # --- Expenses Page ---
    elif page == "Expenses":
        st.title("💳 Expense Tracker")
        
        with st.form("expenses_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            category = col1.selectbox("Category", ["Mileage", "Gas", "Lodging", "Food", "Materials", "Other"])
            amount = col2.number_input("Amount ($)", step=0.01)
            expense_date = col1.date_input("Date", date.today())
            description = st.text_area("Description")
            
            submitted = st.form_submit_button("Log Expense")
            if submitted and amount:
                if sheet:
                    ws = sheet.worksheet('Expenses')
                    ws.append_row([category, amount, str(expense_date), description])
                    st.success("Expense Logged!")

    # --- Mileage Page ---
    elif page == "Mileage":
        st.title("🚗 Mileage Tracker")
        
        with st.form("mileage_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            mileage_date = col1.date_input("Date", date.today())
            license_plate = col2.text_input("License Plate")
            vehicle = col1.text_input("Vehicle")
            vehicle_type = col2.selectbox("Type", ["Personal", "Company", "Rental"])
            
            col3, col4 = st.columns(2)
            start_odo = col3.number_input("Starting Odometer", step=0.1)
            end_odo = col4.number_input("Ending Odometer", step=0.1)
            
            submitted = st.form_submit_button("Calculate & Log")
            
            if submitted:
                total_miles = end_odo - start_odo
                reimbursement = total_miles * 0.65
                reimbursement_str = f"${reimbursement:.2f}"
                
                st.info(f"Total Miles: {total_miles:.1f} | Reimbursement: {reimbursement_str}")
                
                if sheet:
                    ws = sheet.worksheet('Mileage')
                    ws.append_row([
                        str(mileage_date), license_plate, vehicle, vehicle_type, 
                        start_odo, end_odo, total_miles, reimbursement_str
                    ])
                    st.success("Mileage Logged!")
