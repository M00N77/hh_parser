import os
from dotenv import load_dotenv

load_dotenv()

HH_RESPONSES_URL = os.getenv("HH_RESPONSES_URL", "https://hh.ru/applicant/negotiations")

GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "google_creds.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "HH Outreach")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

MIN_DELAY = float(os.getenv("MIN_DELAY", "2"))
MAX_DELAY = float(os.getenv("MAX_DELAY", "5"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "200"))

VALIDATE_MX = os.getenv("VALIDATE_MX", "1") == "1"

# Файлы данных
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STORAGE_STATE = os.path.join(DATA_DIR, "hh_state.json")
RESPONSES_JSON = os.path.join(DATA_DIR, "responses.json")
ENRICHED_JSON = os.path.join(DATA_DIR, "enriched.json")

# Мусорные домены/адреса для отсева email
EMAIL_BLACKLIST_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "domain.com",
    "email.com", "yourdomain.com", "test.com",
}
EMAIL_BLACKLIST_PREFIX = {"no-reply", "noreply", "info@example"}
