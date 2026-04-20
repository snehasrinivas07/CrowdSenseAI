import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://crowdsense-frontend-417095097143.asia-south1.run.app"
)
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)
WS_INTERVAL_SECONDS = 5
MAX_WAIT_MINUTES = 18
