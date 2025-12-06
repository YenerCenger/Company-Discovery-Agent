"""
Database initialization script
Run this to create all database tables
"""
from database.session import init_db
from config.logging_config import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully!")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True)
        raise
