"""Database connection and session management"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from .config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    # Test path only: one shared connection across threads (the pcap/edge code
    # opens SessionLocal from worker threads and asyncio.to_thread).
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Production PostgreSQL engine
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections are alive before using
        # Limit compiled statement cache to prevent memory bloat from large
        # batch INSERT statements with varying row counts (background tasks
        # generate thousands of KPIs per cycle).
        query_cache_size=128,
    )

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
        # Only commit if there are pending changes (skip for read-only requests)
        if db.dirty or db.new or db.deleted:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Initialize database
def init_db():
    """Initialize database with table creation, migrations, and validation"""
    Base.metadata.create_all(bind=engine)
    # Run migrations for new columns
    _run_migrations()
    # Validate database is ready
    _validate_db_connection()


def _validate_db_connection():
    """Test database connection before proceeding"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection validated")
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        raise


def _run_migrations():
    """Run database migrations to add new columns to existing tables"""
    from sqlalchemy import text

    migrations = [
        # System Settings - Slack integration columns
        ("system_settings", "slack_enabled", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_enabled BOOLEAN DEFAULT FALSE"),
        ("system_settings", "slack_webhook_url", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_webhook_url VARCHAR"),
        ("system_settings", "slack_channel", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_channel VARCHAR DEFAULT '#network-alerts'"),
        ("system_settings", "slack_notify_alerts", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_notify_alerts BOOLEAN DEFAULT TRUE"),
        ("system_settings", "slack_notify_actions", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_notify_actions BOOLEAN DEFAULT TRUE"),
        ("system_settings", "slack_notify_critical_only", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS slack_notify_critical_only BOOLEAN DEFAULT FALSE"),
        # CARTO basemap settings (map tiles)
        ("system_settings", "carto_api_key", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS carto_api_key VARCHAR"),
        ("system_settings", "carto_basemap", "ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS carto_basemap VARCHAR"),
        # Cable network specific migrations
        ("alerts", "affected_customers", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS affected_customers INTEGER DEFAULT 0"),
        ("alerts", "affected_modems", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS affected_modems INTEGER DEFAULT 0"),
        ("self_healing_actions", "ticket_id", "ALTER TABLE self_healing_actions ADD COLUMN IF NOT EXISTS ticket_id VARCHAR"),
        ("self_healing_actions", "escalation_reason", "ALTER TABLE self_healing_actions ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR"),
        # Two-model LLM: optional generalist writer model (analyst = security model),
        # optionally on its own provider/endpoint/key.
        ("llm_config", "writer_model_name", "ALTER TABLE llm_config ADD COLUMN IF NOT EXISTS writer_model_name VARCHAR"),
        ("llm_config", "writer_provider", "ALTER TABLE llm_config ADD COLUMN IF NOT EXISTS writer_provider VARCHAR"),
        ("llm_config", "writer_endpoint_url", "ALTER TABLE llm_config ADD COLUMN IF NOT EXISTS writer_endpoint_url VARCHAR"),
        ("llm_config", "writer_api_key", "ALTER TABLE llm_config ADD COLUMN IF NOT EXISTS writer_api_key VARCHAR"),
        # S3 staging config on the cloudera_services row (edge pcap staging)
        ("cloudera_services", "s3_staging_enabled", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_enabled BOOLEAN DEFAULT FALSE"),
        ("cloudera_services", "s3_staging_endpoint_url", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_endpoint_url VARCHAR"),
        ("cloudera_services", "s3_staging_access_key", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_access_key VARCHAR"),
        ("cloudera_services", "s3_staging_secret_key", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_secret_key VARCHAR"),
        ("cloudera_services", "s3_staging_bucket", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_bucket VARCHAR"),
        ("cloudera_services", "s3_staging_region", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_region VARCHAR"),
        ("cloudera_services", "s3_staging_prefix", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_prefix VARCHAR DEFAULT 'edge-captures'"),
        ("cloudera_services", "s3_staging_status", "ALTER TABLE cloudera_services ADD COLUMN IF NOT EXISTS s3_staging_status VARCHAR DEFAULT 'disconnected'"),
    ]

    with engine.connect() as conn:
        for table, column, sql in migrations:
            try:
                # Check if column exists first - use parameterized query to prevent SQL injection
                check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name")
                result = conn.execute(check_query, {"table_name": table, "column_name": column})
                if result.fetchone() is None:
                    # Column doesn't exist, add it
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Added column {column} to {table}")
            except Exception as e:
                # Fallback: try without IF NOT EXISTS for broader compatibility
                try:
                    check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name")
                    result = conn.execute(check_query, {"table_name": table, "column_name": column})
                    if result.fetchone() is None:
                        simple_sql = sql.replace(" IF NOT EXISTS", "")
                        conn.execute(text(simple_sql))
                        conn.commit()
                        print(f"✅ Added column {column} to {table}")
                except Exception as e2:
                    # Column might already exist - log for visibility
                    print(f"⚠️ Migration note for {table}.{column}: {e2}")
