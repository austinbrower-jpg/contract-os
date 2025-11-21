import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import pandas as pd
from datetime import date, datetime, timedelta
import time

# --- Page Configuration ---
st.set_page_config(page_title="Battle Bound Branding", page_icon="🔒", layout="wide")

# --- Session State Initialization ---
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "password" not in st.session_state:
    st.session_state["password"] = ""
if "data_backup" not in st.session_state:
    st.session_state["data_backup"] = {}

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
        'Directory': ['Name', 'Company', 'Email', 'Phone', 'Address', 'Pay Rate'],
        'Hours': ['Employee', 'Date', 'Hours', 'Task', 'Contract'],
        'Expenses': ['Category', 'Amount', 'Date', 'Description', 'Contract'],
        'Mileage': ['Date', 'License', 'Vehicle', 'Vehicle Type', 'Starting Odometer', 'Ending Odometer', 'Total Miles', 'Reimbursement Amount'],
        'Pipeline_Contracts': ['Name', 'Notice ID', 'Contract Type', 'Contact Name', 'Contact Email', 'Date Offers Due', 'Inactive Date', 'Publish Date', 'Notes'],
        'Pipeline_Companies': ['Company Name', 'Contact Name', 'Contact Email', 'Contact Phone', 'Contacted', 'Facebook URL'],
        'Active_Contracts': ['Contract Name', 'Agency', 'Contract Number', 'Start Date', 'End Date', 'Total Ceiling Value', 'Status', 'Notes'],
        'Invoices': ['Invoice Number', 'Contract', 'Date Sent', 'Due Date', 'Amount', 'Status', 'Notes']
    }

    for name, headers in tables.items():
        try:
            worksheet = sheet.worksheet(name)
            # Check if empty and add headers if needed
            existing_headers = worksheet.row_values(1)
            if not existing_headers:
                worksheet.append_row(headers)
            else:
                # Check for missing columns and append them if necessary
                for i, header in enumerate(headers):
                    if header not in existing_headers:
                        worksheet.update_cell(1, len(existing_headers) + 1, header)
                        existing_headers.append(header) 
                
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=name, rows=100, cols=20)
            worksheet.append_row(headers)

@st.cache_data(ttl=60) # Aggressive Caching: 60 seconds
def load_data(_sheet, worksheet_name):
    """Fetches data from a worksheet and returns it as a DataFrame. Handles 429 Errors."""
    if not _sheet:
        return pd.DataFrame()
    
    try:
        ws = _sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Success! Update the backup in session state
        st.session_state["data_backup"][worksheet_name] = df
        return df
        
    except Exception as e:
        error_str = str(e)
        # Check for Quota Exceeded / 429
        if "429" in error_str or "Quota exceeded" in error_str:
            st.warning(f"🚦 Speed Limit Hit (429). Displaying cached data for {worksheet_name}. Please wait 60s.")
            # Attempt to return backup
            if worksheet_name in st.session_state["data_backup"]:
                return st.session_state["data_backup"][worksheet_name]
            else:
                st.error("Quota exceeded and no cached data available.")
                return pd.DataFrame()
        else:
            st.error(f"Error loading {worksheet_name}: {e}")
            return pd.DataFrame()

def clear_cache():
    st.cache_data.clear()
    st.toast("Cache Cleared! Fetching fresh data...", icon="🔄")

# --- Authentication ---
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user = st.session_state.get("username", "")
        pw = st.session_state.get("password", "")
        
        if user == "admin" and pw == "battlebound2025":
            st.session_state["password_correct"] = True
            st.session_state["username"] = "" 
            st.session_state["password"] = ""
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        
        if st.session_state.get("password_correct") is False:
            if st.session_state.get("username") or st.session_state.get("password"):
                st.error("😕 User not known or password incorrect")
        return False
    
    return True

# --- Main App Logic ---
if check_password():
    # Initialize Sheet
    sheet = get_db_connection()
    # Only init_sheet on first load to save quota, or handle errors gracefully
    if sheet:
        try:
            init_sheet(sheet)
        except Exception as e:
            if "429" in str(e):
                st.warning("Could not verify sheet structure due to quota limits. Proceeding with cached data.")

    # --- Sidebar ---
    if os.path.exists("BBLogo.png"):
        st.sidebar.image("BBLogo.png", use_container_width=True)
    else:
        st.sidebar.title("Battle Bound Branding")
        
    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate", ["Home", "Pipeline", "Active Contracts", "Invoices", "Directory", "Hours", "Expenses", "Mileage"])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data"):
        clear_cache()
        st.rerun()
        
    if st.sidebar.button("Logout"):
        st.session_state["password_correct"] = False
        st.rerun()

    # --- Home Page ---
    if page == "Home":
        st.title("Battle Bound Branding")
        st.subheader("Company Operation Center")
        st.divider()
        
        # Load Data for Metrics (Cached)
        df_dir = load_data(sheet, "Directory")
        df_exp = load_data(sheet, "Expenses")
        df_mil = load_data(sheet, "Mileage")
        df_active_contracts = load_data(sheet, "Active_Contracts")
        
        # Calculate Metrics
        active_members = len(df_dir) if not df_dir.empty else 0
        active_contracts_count = len(df_active_contracts[df_active_contracts['Status'] == 'Active']) if not df_active_contracts.empty and 'Status' in df_active_contracts.columns else 0
        
        pending_expenses = 0.0
        if not df_exp.empty and 'Amount' in df_exp.columns:
            if df_exp['Amount'].dtype == object:
                 df_exp['Amount'] = df_exp['Amount'].replace('[\$,]', '', regex=True).astype(float)
            pending_expenses = df_exp['Amount'].sum()
            
        ytd_mileage = 0.0
        if not df_mil.empty and 'Total Miles' in df_mil.columns:
             ytd_mileage = pd.to_numeric(df_mil['Total Miles'], errors='coerce').sum()

        # Display Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active Contracts", str(active_contracts_count))
        col2.metric("Team Members", str(active_members))
        col3.metric("Pending Expenses", f"${pending_expenses:,.2f}")
        col4.metric("YTD Mileage", f"{ytd_mileage:,.1f} mi")
        
        st.markdown("### Recent Activity")
        st.info("System initialized. Dashboard data is cached for performance.")

    # --- Pipeline Page ---
    elif page == "Pipeline":
        st.title("🚀 Opportunity Pipeline")
        
        pipeline_type = st.radio("Select Pipeline Type", ["Track Contract", "Track Company"], horizontal=True)
        st.divider()

        if pipeline_type == "Track Contract":
            st.subheader("📝 New Contract Opportunity")
            with st.form("pipeline_contract_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                name = col1.text_input("Opportunity Name")
                notice_id = col2.text_input("Notice ID")
                
                col3, col4 = st.columns(2)
                contract_type = col3.selectbox("Contract Type", ["Federal", "State", "Commercial", "Sub-Contract", "Other"])
                contact_name = col4.text_input("Point of Contact Name")
                contact_email = st.text_input("Point of Contact Email")
                
                col5, col6, col7 = st.columns(3)
                offers_due = col5.date_input("Date Offers Due", date.today())
                inactive_date = col6.date_input("Inactive Date", date.today())
                publish_date = col7.date_input("Publish Date", date.today())
                
                notes = st.text_area("Notes / Description")
                
                submitted = st.form_submit_button("Add to Pipeline")
                if submitted and name:
                    if sheet:
                        try:
                            ws = sheet.worksheet('Pipeline_Contracts')
                            ws.append_row([
                                name, notice_id, contract_type, contact_name, contact_email, 
                                str(offers_due), str(inactive_date), str(publish_date), notes
                            ])
                            st.success("Contract Opportunity Added!")
                            clear_cache()
                        except Exception as e:
                            st.error(f"Error saving: {e}")
                    else:
                         st.warning("Saved locally (No DB connection)")
            
            # Show Data
            st.subheader("📊 Existing Opportunities")
            df = load_data(sheet, "Pipeline_Contracts")
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No contract opportunities tracked yet.")

        elif pipeline_type == "Track Company":
            st.subheader("🏢 New Company Lead")
            with st.form("pipeline_company_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                company_name = col1.text_input("Company Name")
                contact_name = col2.text_input("Contact Name")
                
                col3, col4 = st.columns(2)
                contact_email = col3.text_input("Contact Email")
                contact_phone = col4.text_input("Contact Phone")
                
                col5, col6 = st.columns(2)
                contacted = col5.selectbox("Has been contacted?", ["No", "Yes"])
                fb_url = col6.text_input("Facebook URL")
                
                submitted = st.form_submit_button("Add Company Lead")
                if submitted and company_name:
                    if sheet:
                        try:
                            ws = sheet.worksheet('Pipeline_Companies')
                            ws.append_row([
                                company_name, contact_name, contact_email, contact_phone, 
                                contacted, fb_url
                            ])
                            st.success("Company Lead Added!")
                            clear_cache()
                        except Exception as e:
                            st.error(f"Error saving: {e}")
                    else:
                        st.warning("Saved locally (No DB connection)")

            # Show Data
            st.subheader("📇 Company Leads")
            df = load_data(sheet, "Pipeline_Companies")
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No company leads tracked yet.")

    # --- Active Contracts Page ---
    elif page == "Active Contracts":
        st.title("📜 Active Contracts")
        
        # Metrics
        df_active = load_data(sheet, "Active_Contracts")
        
        total_value = 0.0
        days_remaining = "N/A"
        
        if not df_active.empty:
            if 'Total Ceiling Value' in df_active.columns:
                 if df_active['Total Ceiling Value'].dtype == object:
                     vals = df_active['Total Ceiling Value'].replace('[\$,]', '', regex=True)
                     total_value = pd.to_numeric(vals, errors='coerce').sum()
                 else:
                     total_value = df_active['Total Ceiling Value'].sum()
            
            if 'End Date' in df_active.columns:
                df_active['End Date'] = pd.to_datetime(df_active['End Date'], errors='coerce')
                today = pd.to_datetime(date.today())
                future_dates = df_active[df_active['End Date'] > today]['End Date']
                if not future_dates.empty:
                    min_days = (future_dates.min() - today).days
                    days_remaining = f"{min_days} Days"

        col1, col2 = st.columns(2)
        col1.metric("Total Contract Value", f"${total_value:,.2f}")
        col2.metric("Days Remaining (Soonest)", days_remaining)
        
        st.divider()
        
        # Add Contract Form
        st.subheader("➕ Add New Contract")
        with st.form("active_contracts_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            contract_name = col1.text_input("Contract Name")
            agency = col2.text_input("Agency (e.g., VA, DoD)")
            
            col3, col4 = st.columns(2)
            contract_number = col3.text_input("Contract Number")
            status = col4.selectbox("Status", ["Active", "Paused", "Completed"])
            
            col5, col6, col7 = st.columns(3)
            start_date = col5.date_input("Start Date", date.today())
            end_date = col6.date_input("End Date", date.today())
            ceiling_value = col7.number_input("Total Ceiling Value ($)", min_value=0.0, step=1000.0)
            
            notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Activate Contract")
            if submitted and contract_name:
                if sheet:
                    try:
                        ws = sheet.worksheet('Active_Contracts')
                        ws.append_row([
                            contract_name, agency, contract_number, 
                            str(start_date), str(end_date), ceiling_value, status, notes
                        ])
                        st.success("Contract Activated!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
                else:
                    st.warning("Saved locally (No DB connection)")
        
        # Show Data
        st.subheader("📋 Active Contracts List")
        if not df_active.empty:
            if 'End Date' in df_active.columns:
                 df_active['End Date'] = df_active['End Date'].dt.date
            st.dataframe(df_active, use_container_width=True)
        else:
            st.info("No active contracts found.")

    # --- Invoices Page ---
    elif page == "Invoices":
        st.title("💸 Invoicing & Revenue")
        
        # Load Data
        df_invoices = load_data(sheet, "Invoices")
        df_active = load_data(sheet, "Active_Contracts")
        
        # Metrics Calculation
        outstanding_revenue = 0.0
        collected_ytd = 0.0
        overdue_count = 0
        
        if not df_invoices.empty:
            if 'Amount' in df_invoices.columns:
                if df_invoices['Amount'].dtype == object:
                    df_invoices['Amount'] = df_invoices['Amount'].replace('[\$,]', '', regex=True).astype(float)
            
            if 'Due Date' in df_invoices.columns:
                df_invoices['Due Date'] = pd.to_datetime(df_invoices['Due Date'], errors='coerce')
            
            outstanding_revenue = df_invoices[df_invoices['Status'] == 'Sent']['Amount'].sum()
            collected_ytd = df_invoices[df_invoices['Status'] == 'Paid']['Amount'].sum()
            
            today = pd.to_datetime(date.today())
            overdue_mask = (df_invoices['Status'] != 'Paid') & (df_invoices['Status'] != 'Cancelled') & (df_invoices['Due Date'] < today)
            overdue_count = overdue_mask.sum()
            
            df_invoices.loc[overdue_mask, 'Status'] = '⚠️ OVERDUE'

        col1, col2, col3 = st.columns(3)
        col1.metric("Outstanding Revenue", f"${outstanding_revenue:,.2f}")
        col2.metric("Collected YTD", f"${collected_ytd:,.2f}")
        col3.metric("Overdue Invoices", str(overdue_count), delta_color="inverse")
        
        st.divider()
        
        # Add Invoice Form
        st.subheader("🧾 Create Invoice")
        with st.form("invoice_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            invoice_number = col1.text_input("Invoice Number")
            
            # Dropdown for Contract (Cached)
            if not df_active.empty and 'Contract Name' in df_active.columns:
                contract = col2.selectbox("Contract", df_active['Contract Name'].sort_values().unique())
            else:
                contract = col2.text_input("Contract")
            
            col3, col4 = st.columns(2)
            date_sent = col3.date_input("Date Sent", date.today())
            due_date = col4.date_input("Due Date", date.today() + timedelta(days=30))
            
            col5, col6 = st.columns(2)
            amount = col5.number_input("Amount ($)", min_value=0.0, step=100.0)
            status = col6.selectbox("Status", ["Draft", "Sent", "Paid", "Overdue", "Cancelled"])
            
            notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Save Invoice")
            if submitted and invoice_number:
                if sheet:
                    try:
                        ws = sheet.worksheet('Invoices')
                        ws.append_row([
                            invoice_number, contract, str(date_sent), str(due_date), 
                            amount, status, notes
                        ])
                        st.success("Invoice Saved!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
                else:
                    st.warning("Saved locally (No DB connection)")
        
        # Show Data
        st.subheader("🗂 Invoice Log")
        if not df_invoices.empty:
            if 'Due Date' in df_invoices.columns:
                 df_invoices['Due Date'] = df_invoices['Due Date'].dt.date
            if 'Date Sent' in df_invoices.columns:
                 df_invoices['Date Sent'] = pd.to_datetime(df_invoices['Date Sent'], errors='coerce').dt.date
                 
            df_invoices = df_invoices.sort_values('Due Date', ascending=False)
            st.dataframe(df_invoices, use_container_width=True)
        else:
            st.info("No invoices found.")

    # --- Directory Page ---
    elif page == "Directory":
        st.title("👥 Directory")
        
        with st.form("directory_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name")
            company = col2.text_input("Company")
            email = col1.text_input("Email")
            phone = col2.text_input("Phone")
            address = st.text_area("Address")
            pay_rate = col1.number_input("Hourly Pay Rate ($)", min_value=0.0, step=0.5)
            
            submitted = st.form_submit_button("Save Contact")
            if submitted and name:
                if sheet:
                    try:
                        ws = sheet.worksheet('Directory')
                        ws.append_row([name, company, email, phone, address, pay_rate])
                        st.success("Contact Saved!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
                else:
                    st.warning("Saved locally (No DB connection)")

        # Show Data
        df = load_data(sheet, "Directory")
        if not df.empty:
            if 'Name' in df.columns:
                df = df.sort_values('Name')
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No contacts found.")

    # --- Hours Page (Payroll) ---
    elif page == "Hours":
        st.title("⏱️ Hour Tracker & Payroll")
        
        # 1. Payroll Summary Section
        st.subheader("💰 Payroll Summary")
        
        df_hours = load_data(sheet, "Hours")
        df_dir = load_data(sheet, "Directory")
        df_active = load_data(sheet, "Active_Contracts")
        
        if not df_hours.empty and not df_dir.empty:
            df_hours['Hours'] = pd.to_numeric(df_hours['Hours'], errors='coerce').fillna(0)
            
            payroll = df_hours.groupby('Employee')['Hours'].sum().reset_index()
            payroll.columns = ['Employee', 'Total Hours']
            
            if 'Name' in df_dir.columns and 'Pay Rate' in df_dir.columns:
                df_dir['Pay Rate'] = pd.to_numeric(df_dir['Pay Rate'], errors='coerce').fillna(0)
                
                merged = pd.merge(payroll, df_dir[['Name', 'Pay Rate']], left_on='Employee', right_on='Name', how='left')
                merged['Pay Rate'] = merged['Pay Rate'].fillna(0)
                merged['Est. Total Pay'] = merged['Total Hours'] * merged['Pay Rate']
                
                display_df = merged[['Employee', 'Total Hours', 'Pay Rate', 'Est. Total Pay']].copy()
                display_df['Est. Total Pay'] = display_df['Est. Total Pay'].apply(lambda x: f"${x:,.2f}")
                display_df['Pay Rate'] = display_df['Pay Rate'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("Directory missing 'Name' or 'Pay Rate' columns. Cannot calculate pay.")
                st.dataframe(payroll, use_container_width=True)
        else:
            st.info("No hours logged yet.")

        st.divider()
        
        # 2. Log Hours Form
        st.subheader("📝 Log New Shift")
        with st.form("hours_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            # Dropdown for employee (Cached)
            if not df_dir.empty and 'Name' in df_dir.columns:
                employee = col1.selectbox("Employee Name", df_dir['Name'].sort_values().unique())
            else:
                employee = col1.text_input("Employee Name")
            
            # Dropdown for Contract (Cached)
            if not df_active.empty and 'Contract Name' in df_active.columns:
                contract = col2.selectbox("Contract / Project", df_active['Contract Name'].sort_values().unique())
            else:
                contract = col2.text_input("Contract / Project", value="General")

            col3, col4 = st.columns(2)
            work_date = col3.date_input("Date", date.today())
            hours = col4.number_input("Hours Worked", step=0.5)
            task = st.text_area("Task / Description")
            
            submitted = st.form_submit_button("Log Hours")
            if submitted and employee:
                if sheet:
                    try:
                        ws = sheet.worksheet('Hours')
                        ws.append_row([employee, str(work_date), hours, task, contract])
                        st.success("Hours Logged!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
        
        # 3. Raw Log
        if not df_hours.empty:
            st.markdown("### Detailed Log")
            if 'Date' in df_hours.columns:
                df_hours['Date'] = pd.to_datetime(df_hours['Date'], errors='coerce')
                df_hours = df_hours.sort_values('Date', ascending=False)
                df_hours['Date'] = df_hours['Date'].dt.date
            st.dataframe(df_hours, use_container_width=True)

    # --- Expenses Page ---
    elif page == "Expenses":
        st.title("💳 Expense Tracker")
        
        df_active = load_data(sheet, "Active_Contracts")
        
        with st.form("expenses_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            category = col1.selectbox("Category", ["Mileage", "Gas", "Lodging", "Food", "Materials", "Other"])
            
            # Dropdown for Contract (Cached)
            if not df_active.empty and 'Contract Name' in df_active.columns:
                contract = col2.selectbox("Contract / Project", df_active['Contract Name'].sort_values().unique())
            else:
                contract = col2.text_input("Contract / Project", value="General")
            
            col3, col4 = st.columns(2)
            amount = col3.number_input("Amount ($)", step=0.01)
            expense_date = col4.date_input("Date", date.today())
            
            description = st.text_area("Description")
            
            submitted = st.form_submit_button("Log Expense")
            if submitted and amount:
                if sheet:
                    try:
                        ws = sheet.worksheet('Expenses')
                        ws.append_row([category, amount, str(expense_date), description, contract])
                        st.success("Expense Logged!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")

        # Show Data
        df = load_data(sheet, "Expenses")
        if not df.empty:
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.sort_values('Date', ascending=False)
                df['Date'] = df['Date'].dt.date
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No expenses found.")

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
                    try:
                        ws = sheet.worksheet('Mileage')
                        ws.append_row([
                            str(mileage_date), license_plate, vehicle, vehicle_type, 
                            start_odo, end_odo, total_miles, reimbursement_str
                        ])
                        st.success("Mileage Logged!")
                        clear_cache()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
