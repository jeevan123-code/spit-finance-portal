"""
Configuration for the SPIT Student Council Finance Management Portal.

The architecture is PostgreSQL-ready: development uses SQLite for zero-setup,
while production reads DATABASE_URL (e.g. a PostgreSQL DSN) from the
environment. No code changes are needed to switch — only the env var.
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # survives dropped PostgreSQL connections
    }

    # Session / security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_TIME_LIMIT = None
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # File uploads (Document Repository)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "finance_portal", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB per upload
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "csv"}

    # Organisation branding (used on generated PDFs)
    ORG_NAME = "Sardar Patel Institute of Technology"
    ORG_SUBTITLE = "Student Council — Finance Management Portal"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "finance_portal.db"),
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    # In production set DATABASE_URL to your PostgreSQL DSN, e.g.
    #   postgresql+psycopg2://user:pass@host:5432/spit_finance
    # If unset (e.g. a free demo host with no managed DB), fall back to SQLite
    # so the app still boots and serves the live demo.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "finance_portal.db"),
    )

    @classmethod
    def init_app(cls, app):
        # Render/Heroku style URLs sometimes start with postgres:// — normalise.
        uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
        if uri.startswith("postgres://"):
            app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace(
                "postgres://", "postgresql://", 1
            )


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
