"""
Database connection and session management.

Manages SQLAlchemy engine and sessions with MySQL database.
Configuration loaded from environment variables.
"""

import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from missing_file_check.storage.models import Base


class DatabaseManager:
    """
    Database connection manager.

    Manages SQLAlchemy engine and session creation.
    Configuration loaded from environment variables:
    - DB_HOST: Database host
    - DB_PORT: Database port (default 3306)
    - DB_USER: Database user
    - DB_PASSWORD: Database password
    - DB_NAME: Database name
    - DB_CHARSET: Character set (default utf8mb4)
    - DB_POOL_SIZE: Connection pool size (default 5)
    - DB_MAX_OVERFLOW: Max overflow connections (default 10)
    """

    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            connection_url: Optional database URL. If not provided,
                          will be constructed from environment variables.
        """
        if connection_url:
            self.connection_url = connection_url
        else:
            self.connection_url = self._build_connection_url()

        self.engine = None
        self.SessionLocal = None

    def _build_connection_url(self) -> str:
        """
        Build database connection URL from environment variables.

        Returns:
            Database connection URL

        Raises:
            ValueError: If required environment variables are missing
        """
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT", "3306")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")
        charset = os.getenv("DB_CHARSET", "utf8mb4")

        if not all([host, user, password, database]):
            raise ValueError(
                "Missing required database environment variables: "
                "DB_HOST, DB_USER, DB_PASSWORD, DB_NAME"
            )

        # Use pymysql as MySQL driver
        return (
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            f"?charset={charset}"
        )

    def initialize(self):
        """
        Initialize database engine and session factory.

        Creates SQLAlchemy engine with connection pooling.
        """
        if self.engine is not None:
            return

        pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

        # Create engine with connection pool
        self.engine = create_engine(
            self.connection_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def get_session(self) -> Session:
        """
        Create a new database session.

        Returns:
            SQLAlchemy session

        Raises:
            RuntimeError: If database not initialized
        """
        if self.SessionLocal is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() first."
            )

        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations.

        Usage:
            with db_manager.session_scope() as session:
                session.add(obj)
                # Automatically commits on success, rollback on error

        Yields:
            SQLAlchemy session
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self):
        """
        Create all tables defined in models.

        Note: This is for development/testing. In production, use
        proper migration tools like Alembic.
        """
        if self.engine is None:
            self.initialize()

        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """
        Drop all tables.

        Warning: This will delete all data. Use with caution.
        """
        if self.engine is None:
            self.initialize()

        Base.metadata.drop_all(bind=self.engine)

    def close(self):
        """Close database engine and connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def init_db(connection_url: Optional[str] = None):
    """
    Initialize global database manager.

    Args:
        connection_url: Optional database URL
    """
    global _db_manager
    _db_manager = DatabaseManager(connection_url)
    _db_manager.initialize()


def get_session() -> Session:
    """
    Get a new database session from global manager.

    Returns:
        SQLAlchemy session
    """
    return get_db_manager().get_session()


@contextmanager
def session_scope():
    """
    Provide a transactional scope using global manager.

    Yields:
        SQLAlchemy session
    """
    with get_db_manager().session_scope() as session:
        yield session
