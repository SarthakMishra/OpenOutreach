# api_server/db/engine.py
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from api_server.db.models import Base

logger = logging.getLogger(__name__)

# Server DB path (separate from per-account profile DBs)
SERVER_DB_PATH = Path(__file__).parent.parent.parent / "assets" / "server.db"

# Cache the engine to avoid recreating it
_engine = None


def get_engine():
    """Get SQLAlchemy engine for server database."""
    global _engine
    if _engine is None:
        SERVER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{SERVER_DB_PATH}"
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
        # Create tables if they don't exist (checkfirst=True prevents errors if tables already exist)
        Base.metadata.create_all(bind=_engine, checkfirst=True)
        logger.debug("Server DB schema ready → %s", SERVER_DB_PATH.name)
    return _engine


def get_session():
    """Get database session for server database."""
    engine = get_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    return Session()
