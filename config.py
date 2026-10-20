"""
config.py
---------
Central configuration for the AI Business Assistant.
All secrets are read dynamically from environment variables (via python-dotenv),
never hard-coded here.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file (if present) into the environment
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))


class classproperty:
    """Descriptor that acts like @property but for class-level access."""
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, owner=None):
        target = owner if owner is not None else type(obj)
        return self.func(target)


class Config:
    # --- Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "False" if IS_VERCEL else "True") == "True"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Database (evaluates dynamically from environment) ---
    @classproperty
    def SQLALCHEMY_DATABASE_URI(cls):
        env_db = (
            os.environ.get("DATABASE_URL")
            or os.environ.get("POSTGRES_URL")
            or os.environ.get("POSTGRES_PRISMA_URL")
        )
        # Fallback to Neon/Postgres individual connection variables if present
        if not env_db and os.environ.get("POSTGRES_HOST") and os.environ.get("PGPASSWORD"):
            user = os.environ.get("PGUSER", "default")
            pw = os.environ.get("PGPASSWORD", "")
            host = os.environ.get("POSTGRES_HOST", "")
            db_name = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DATABASE", "neondb")
            env_db = f"postgresql://{user}:{pw}@{host}/{db_name}?sslmode=require"

        if env_db:
            if env_db.startswith("postgres://"):
                env_db = env_db.replace("postgres://", "postgresql://", 1)
            return env_db
        if IS_VERCEL:
            return "sqlite:////tmp/app.db"
        return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"

    # --- LLM / Demo Mode (evaluates dynamically so env changes take effect immediately) ---
    @classproperty
    def LLM_PROVIDER(cls):
        return os.environ.get("LLM_PROVIDER", "none").lower()

    @classproperty
    def LLM_API_KEY(cls):
        return os.environ.get("LLM_API_KEY", "")

    @classproperty
    def LLM_API_BASE(cls):
        return os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")

    @classproperty
    def LLM_MODEL(cls):
        return os.environ.get("LLM_MODEL", "gpt-4o-mini")

    @classproperty
    def DEMO_MODE(cls):
        provider = os.environ.get("LLM_PROVIDER", "none").lower()
        key = os.environ.get("LLM_API_KEY", "").strip()
        return (provider == "none") or (key == "")

    # --- Paths used across the app ---
    DATA_DIR = os.path.join(BASE_DIR, "data")
    KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
    ML_DIR = os.path.join(BASE_DIR, "ml")
    REPORTS_DIR = os.environ.get("REPORTS_DIR", "/tmp/reports" if IS_VERCEL else os.path.join(BASE_DIR, "reports"))
    MODEL_PATH = os.path.join(ML_DIR, "model.pkl")
    ENCODERS_PATH = os.path.join(ML_DIR, "encoders.pkl")
    SEGMENTATION_MODEL_PATH = os.path.join(ML_DIR, "segmentation_model.pkl")
