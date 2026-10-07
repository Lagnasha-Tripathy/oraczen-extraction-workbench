import os
from pathlib import Path

# Base directories
# Current file is in backend/app/ -> parent is backend/ -> parent.parent is project root
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Data file path
TICKETS_FILE_PATH = os.getenv(
    "TICKETS_FILE_PATH",
    str(PROJECT_ROOT / "data" / "tickets.jsonl"),
)

# Concurrency & Delay settings
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))
MOCK_DELAY_MS = int(os.getenv("MOCK_DELAY_MS", "200"))
PORT = int(os.getenv("PORT", "8000"))

# CORS settings for frontend connection
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
