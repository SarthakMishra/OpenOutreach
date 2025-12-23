# linkedin/db/accounts.py
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from linkedin.conf import ASSETS_DIR
from linkedin.db.models import Account

logger = logging.getLogger(__name__)

ACCOUNTS_DB_PATH = ASSETS_DIR / "accounts.db"


def _get_session():
    ACCOUNTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{ACCOUNTS_DB_PATH}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Account.__table__.create(bind=engine, checkfirst=True)
    Session = scoped_session(sessionmaker(bind=engine))
    return Session()


def upsert_account(payload: Dict[str, Any]) -> None:
    """
    Create or update an account row. Expects keys:
      handle (required), active, proxy, daily_connections, daily_messages,
      username (required), password (required), booking_link (optional).
    """
    required = ["handle", "username", "password"]
    for key in required:
        if not payload.get(key):
            raise ValueError(f"Missing required field: {key}")

    session = _get_session()
    try:
        handle = payload["handle"]
        row = session.get(Account, handle)
        if row is None:
            row = Account(handle=handle)
            session.add(row)

        row.active = payload.get("active", True)
        row.proxy = payload.get("proxy")
        row.daily_connections = payload.get("daily_connections", 50)
        row.daily_messages = payload.get("daily_messages", 20)
        row.username = payload["username"]
        row.password = payload["password"]
        row.booking_link = payload.get("booking_link")

        session.commit()
        logger.info("Account upserted → %s", handle)
    finally:
        session.close()


def get_account(handle: str) -> Optional[Account]:
    session = _get_session()
    try:
        return session.get(Account, handle)
    finally:
        session.close()


def list_accounts(active_only: bool = False) -> List[Account]:
    session = _get_session()
    try:
        query = session.query(Account)
        if active_only:
            query = query.filter_by(active=True)
        return query.all()
    finally:
        session.close()


def delete_account(handle: str) -> bool:
    session = _get_session()
    try:
        row = session.get(Account, handle)
        if not row:
            return False
        session.delete(row)
        session.commit()
        logger.info("Account deleted → %s", handle)
        return True
    finally:
        session.close()
