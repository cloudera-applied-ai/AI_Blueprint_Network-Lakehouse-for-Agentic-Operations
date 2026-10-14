"""Configuration for Cable Network ISP Data Lakehouse backend"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Get project root directory (parent of backend folder)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env from project root (application/) so DB_PORT etc. are available
_env_path = Path(_PROJECT_ROOT) / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)


def _build_database_url() -> str:
    """Build DATABASE_URL from environment variables set via .project-metadata.yaml."""
    # Use DATABASE_URL directly if provided
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url
    # Otherwise build from individual env vars (also set in .project-metadata.yaml)
    user = os.environ.get("DB_USER", "cable_user")
    password = os.environ.get("DB_PASSWORD", "cable_secure_pass_2024")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "cable_network")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cable Network ISP Data Lakehouse"

    # Database Configuration
    # PostgreSQL for reliable MVCC and proper UPDATE handling
    DATABASE_URL: str = _build_database_url()

    # Infrastructure Scale
    TOTAL_FIBER_NODES: int = 7240
    TOTAL_HEADENDS: int = 42
    TOTAL_HUBS: int = 181
    TOTAL_AMPLIFIERS: int = 28960
    TOTAL_CUSTOMER_ACCOUNTS: int = 1810000
    CUSTOMER_GENERATION_BATCH: int = 5000

    # Data Generation Configuration
    # Every knob below can be overridden with an environment variable of the
    # same name (or in application/.env).
    #
    # Each fiber node gets one KPI row every KPI_GENERATION_INTERVAL_SECONDS.
    # The generator loop ticks every KPI_CYCLE_SECONDS and covers a rotating
    # slice of the plant per tick (nodes * cycle / interval), so the dashboard,
    # alerts, and self-healing keep moving while the row rate stays low.
    # Defaults: 7,240 nodes / 5 min = ~724 rows per 30 s tick, ~87k rows/hour.
    KPI_GENERATION_INTERVAL_SECONDS: int = 300
    KPI_CYCLE_SECONDS: int = 30
    ALERT_CHECK_INTERVAL_SECONDS: int = 10
    HEALING_ACTION_INTERVAL_SECONDS: int = 15

    # Nodes per hub. 0 = use the per-service-area value in constants.py (40).
    NODES_PER_HUB: int = 0

    # Historical backfill on first boot (only when the KPI table is empty).
    # Anything older than RETENTION_RAW_HOURS is deleted by the retention
    # service, so the backfill window should not exceed it.
    HISTORICAL_BACKFILL_HOURS: int = 2
    HISTORICAL_INTERVAL_MINUTES: int = 5

    # Tiered retention (raw -> 1-min -> 5-min -> hourly -> daily). The
    # analytics layer picks the finest tier whose retention covers a query,
    # so shortening a tier degrades granularity, not results.
    RETENTION_RAW_HOURS: int = 2
    RETENTION_1MIN_HOURS: int = 6
    RETENTION_5MIN_HOURS: int = 12
    RETENTION_HOURLY_DAYS: int = 3
    RETENTION_DAILY_DAYS: int = 30
    RETENTION_RESOLVED_ALERTS_DAYS: int = 30
    RETENTION_COMPLETED_ACTIONS_DAYS: int = 30

    # Pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    # API Key Authentication
    API_KEY: str = os.environ.get("API_KEY", "dev-api-key-change-me")

    # CORS – regex applied via allow_origin_regex in main.py
    # Matches localhost, any IP address, any hostname, and *.cloudera.site
    CORS_ORIGIN_REGEX: str = r"https?://.*"

    class Config:
        case_sensitive = True


settings = Settings()
