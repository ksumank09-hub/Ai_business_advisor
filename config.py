"""
config.py
---------
Central configuration for the AI Business Assistant.
All secrets are read from environment variables (via python-dotenv),
never hard-coded here.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file (if present) into the environment
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))


class Config:
    # --- Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "False" if IS_VERCEL else "True") == "True"

    # --- Database ---
    if IS_VERCEL and not os.environ.get("DATABASE_URL"):
        _default_db = "sqlite:////tmp/app.db"
    else:
        _default_db = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"

    _db_url = os.environ.get("DATABASE_URL", _default_db)
    # Fix old 'postgres://' scheme for SQLAlchemy 1.4+
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- LLM / Demo Mode ---
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none").lower()
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
    LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    # The app is considered to be in DEMO MODE whenever no usable API key/provider
    # is configured. This is checked at runtime (see ai/llm.py) so the app never
    # crashes just because an external AI service is unavailable.
    DEMO_MODE = (LLM_PROVIDER == "none") or (LLM_API_KEY.strip() == "")

    # --- Paths used across the app ---
    DATA_DIR = os.path.join(BASE_DIR, "data")
    KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
    ML_DIR = os.path.join(BASE_DIR, "ml")
    REPORTS_DIR = os.environ.get("REPORTS_DIR", "/tmp/reports" if IS_VERCEL else os.path.join(BASE_DIR, "reports"))
    MODEL_PATH = os.path.join(ML_DIR, "model.pkl")
    ENCODERS_PATH = os.path.join(ML_DIR, "encoders.pkl")
    SEGMENTATION_MODEL_PATH = os.path.join(ML_DIR, "segmentation_model.pkl")
