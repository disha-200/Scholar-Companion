# backend/app/__init__.py
from pathlib import Path
from dotenv import load_dotenv

# Load variables from backend/.env  ➜  available to every sub‑module
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
