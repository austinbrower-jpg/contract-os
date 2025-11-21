from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this for production

# Google Sheets Configuration
SHEET_ID = '1QsIKLchwTzC0tAhdgT3JE6TFYRqWS-g5ZNyV5HYglCY'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """Establishes connection to Google Sheets (Cloud Compatible)."""
    creds = None
    
    # 1. Try Cloud Environment Variable (Secrets)
    json_creds = os.environ.get('GOOGLE_CREDENTIALS')
    if json_creds:
        try:
            creds_dict = json.loads(json_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except Exception as e:
            print(f"Error loading credentials from Env: {e}")

    # 2. Fallback to Local File
    if not creds and os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            print(f"Error loading credentials from File: {e}")

    if not creds:
        return None

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {repr(e)}")
        if hasattr(e, 'response'):
             print(f"Response: {e.response.text}")
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple Hardcoded Auth (as requested)
        if username == 'admin' and password == 'battlebound2025':
            session['logged_in'] = True
            flash('Welcome back, Commander.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


def init_sheet():
    """Ensures the necessary worksheets and headers exist."""
    sheet = get_db_connection()
    if not sheet:
        return

    # Define required worksheets and their headers
    tables = {
        'Directory': ['Name', 'Company', 'Email', 'Phone', 'Address'],
        'Hours': ['Employee', 'Date', 'Hours', 'Task'],
        'Expenses': ['Category', 'Amount', 'Date', 'Description'],
        'Mileage': ['Date', 'License', 'Vehicle', 'Vehicle Type', 'Starting Odometer', 'Ending Odometer', 'Total Miles', 'Reimbursement Amount']
    }

    for name, headers in tables.items():
        try:
            worksheet = sheet.worksheet(name)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=name, rows=100, cols=20)
            worksheet.append_row(headers)
            print(f"Created worksheet: {name}")
        
        # Check if headers match (basic check)
        existing_headers = worksheet.row_values(1)
        if not existing_headers:
            worksheet.append_row(headers)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/directory', methods=['GET', 'POST'])
@login_required
def directory():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        company = request.form.get('company')
        address = request.form.get('address')
        
        sheet = get_db_connection()
        if sheet:
            try:
                ws = sheet.worksheet('Directory')
                ws.append_row([name, company, email, phone, address])
                flash('Contact saved to Google Sheet!', 'success')
            except Exception as e:
                flash(f'Error saving to sheet: {str(e)}', 'error')
        else:
            flash('Saved locally (No Google Sheet connection). Check console.', 'warning')
            print(f"Saving Directory: {name}, {company}")
            
        return redirect(url_for('directory'))
    return render_template('directory.html')

@app.route('/hours', methods=['GET', 'POST'])
@login_required
def hours():
    if request.method == 'POST':
        employee = request.form.get('employee')
        date = request.form.get('date')
        hours_worked = request.form.get('hours')
        task = request.form.get('task')
        
        sheet = get_db_connection()
        if sheet:
            try:
                ws = sheet.worksheet('Hours')
                ws.append_row([employee, date, hours_worked, task])
                flash('Hours logged to Google Sheet!', 'success')
            except Exception as e:
                flash(f'Error saving to sheet: {str(e)}', 'error')
        else:
            flash('Saved locally (No Google Sheet connection). Check console.', 'warning')
            print(f"Saving Hours: {employee}, {hours_worked}")
            
        return redirect(url_for('hours'))
    return render_template('hours.html')

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        description = request.form.get('description')
        date = request.form.get('date')
        
        sheet = get_db_connection()
        if sheet:
            try:
                ws = sheet.worksheet('Expenses')
                ws.append_row([category, amount, date, description])
                flash('Expense logged to Google Sheet!', 'success')
            except Exception as e:
                flash(f'Error saving to sheet: {str(e)}', 'error')
        else:
            flash('Saved locally (No Google Sheet connection). Check console.', 'warning')
            print(f"Saving Expense: {category}, {amount}")
            
        return redirect(url_for('expenses'))
    return render_template('expenses.html')

@app.route('/mileage', methods=['GET', 'POST'])
@login_required
def mileage():
    if request.method == 'POST':
        date = request.form.get('date')
        license_plate = request.form.get('license')
        vehicle = request.form.get('vehicle')
        vehicle_type = request.form.get('vehicle_type')
        start_odo = float(request.form.get('start_odo') or 0)
        end_odo = float(request.form.get('end_odo') or 0)
        
        total_miles = end_odo - start_odo
        reimbursement = total_miles * 0.65
        
        # Format for display/storage
        reimbursement_str = f"${reimbursement:.2f}"
        
        sheet = get_db_connection()
        if sheet:
            try:
                ws = sheet.worksheet('Mileage')
                ws.append_row([
                    date, license_plate, vehicle, vehicle_type, 
                    start_odo, end_odo, total_miles, reimbursement_str
                ])
                flash(f'Mileage logged! Reimbursement: {reimbursement_str}', 'success')
            except Exception as e:
                flash(f'Error saving to sheet: {str(e)}', 'error')
        else:
            flash(f'Saved locally. Reimbursement: {reimbursement_str}', 'warning')
            print(f"Saving Mileage: {total_miles} miles, {reimbursement_str}")
            
        return redirect(url_for('mileage'))
    return render_template('mileage.html')

if __name__ == '__main__':
    # Try to initialize the sheet on startup
    try:
        init_sheet()
    except Exception as e:
        print(f"Initialization skipped: {e}")
        
    app.run(debug=True, port=5001)
