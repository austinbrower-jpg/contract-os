import os
import traceback
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')
SHEET_ID = '1QsIKLchwTzC0tAhdgT3JE6TFYRqWS-g5ZNyV5HYglCY'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

print(f"Testing connection with file: {SERVICE_ACCOUNT_FILE}")

try:
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    print("Credentials loaded successfully.")
    
    client = gspread.authorize(creds)
    print("Client authorized.")
    
    sheet = client.open_by_key(SHEET_ID)
    print(f"Sheet opened: {sheet.title}")
    
except Exception:
    traceback.print_exc()
