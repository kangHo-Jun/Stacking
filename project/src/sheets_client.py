import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

MATERIAL_SHEET_ID = "1QrMhSpTttOP1AaOSJoSrY_z5HuExSBxB8mdSxzSKPE8"
VEHICLE_SHEET_ID = "1bfcolHBOnIp42zkuu0tIkBU6tE5SSFZA-tx8qvQMhNc"


def get_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def load_material_sheet():
    client = get_client()
    sheet = client.open_by_key(MATERIAL_SHEET_ID).sheet1
    return sheet.get_all_records()


def load_vehicle_sheet():
    client = get_client()
    sheet = client.open_by_key(VEHICLE_SHEET_ID).sheet1
    return sheet.get_all_records()
