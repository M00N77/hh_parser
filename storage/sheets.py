"""Фаза 5: выгрузка в Google Sheets через service account."""
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_PATH, GOOGLE_SHEET_NAME

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
HEADER = ["company", "vacancy", "vacancy_url", "website", "emails",
          "telegrams", "source", "status", "sent_at"]


def _ws():
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    try:
        sh = gc.open(GOOGLE_SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(GOOGLE_SHEET_NAME)
    ws = sh.sheet1
    if ws.row_values(1) != HEADER:
        ws.update("A1", [HEADER])
    return ws


def write_rows(rows):
    ws = _ws()
    existing = set(r for r in ws.col_values(3)[1:])  # vacancy_url
    new = []
    for r in rows:
        if r.get("vacancy_url") in existing:
            continue
        new.append([
            r.get("company", ""), r.get("vacancy", ""), r.get("vacancy_url", ""),
            r.get("website", ""), "; ".join(r.get("emails", [])),
            "; ".join(r.get("telegrams", [])), r.get("source", ""),
            "new", "",
        ])
    if new:
        ws.append_rows(new, value_input_option="RAW")
    print(f"Записано новых строк: {len(new)}")
    return len(new)
