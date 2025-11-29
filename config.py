import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
)

MAX_CHAT_HISTORY = int(os.environ.get("MAX_CHAT_HISTORY", "50"))
USER_DBS_DIR = "user_dbs"
os.makedirs(USER_DBS_DIR, exist_ok=True)

ENABLE_DETAILED_LOGGING = True
