import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from project root if it exists
load_dotenv()


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-pulse-care-secret-key-change-in-prod")
    APP_NAME = os.environ.get("APP_NAME", "PulseCare HMS")

    # Database Configuration (MySQL)
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_NAME = os.environ.get("DB_NAME", "hospital_management_db")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_POOL_NAME = os.environ.get("DB_POOL_NAME", "hms_pool")
    DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 5))

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(
        days=int(os.environ.get("PERMANENT_SESSION_LIFETIME_DAYS", 7))
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Test environment configuration."""
    DEBUG = False
    TESTING = True
    DB_NAME = os.environ.get("TEST_DB_NAME", "hospital_management_test_db")
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
