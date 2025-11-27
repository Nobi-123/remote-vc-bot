import os

API_ID = int(os.getenv("API_ID", "22657083"))
API_HASH = os.getenv("API_HASH", "d6186691704bd901bdab275ceaab88f3")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8314045999:AAFk45sqRkbIUXdK3F9t0wsKXTvub6l8zfw")
OWNER_ID = int(os.getenv("OWNER_ID", "8449801101"))
PREFIX = os.getenv("PREFIX", "/")

SESSIONS_DIR = "sessions"
RECORDINGS_DIR = "recordings"
TEMP_DIR = "temp"

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

sudo_users = {OWNER_ID}
