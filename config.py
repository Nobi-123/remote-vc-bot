import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
PREFIX = os.getenv("PREFIX", "/", ".", "!")

SESSIONS_DIR = "sessions"
RECORDINGS_DIR = "recordings"
TEMP_DIR = "temp"

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

sudo_users = {OWNER_ID}
