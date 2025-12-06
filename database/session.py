from sqlmodel import create_engine, Session, SQLModel
from contextlib import contextmanager
from typing import Generator
from config.settings import settings


# Create engine once at module level
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions

    Usage:
        with get_db_session() as session:
            # Use session here
            pass
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Initialize database schema
    Creates all tables defined in SQLModel models
    """
    SQLModel.metadata.create_all(engine)
