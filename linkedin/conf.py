# linkedin/conf.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from linkedin.db.models import Account

load_dotenv()

# ----------------------------------------------------------------------
# Paths (all under assets/)
# ----------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

COOKIES_DIR = ASSETS_DIR / "cookies"
DATA_DIR = ASSETS_DIR / "data"

COOKIES_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures"
FIXTURE_PROFILES_DIR = FIXTURE_DIR / "profiles"
FIXTURE_PAGES_DIR = FIXTURE_DIR / "pages"

ACCOUNTS_DB_PATH = ASSETS_DIR / "accounts.db"

MIN_DELAY = 5
MAX_DELAY = 8

OPPORTUNISTIC_SCRAPING = False


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def get_account_config(handle: str) -> Dict[str, Any]:
    """Return full config (public + secrets) for a handle from the accounts DB."""
    session = _get_accounts_session()
    try:
        acct = session.get(Account, handle)
        if not acct:
            raise KeyError(f"Account '{handle}' not found in accounts DB")

        account_db_path = DATA_DIR / f"{handle}.db"

        return {
            "handle": handle,
            "active": bool(acct.active),
            "proxy": acct.proxy,
            "daily_connections": acct.daily_connections,
            "daily_messages": acct.daily_messages,
            # Credentials (consider encrypting/hashing in server layer)
            "username": acct.username,
            "password": acct.password,
            # Runtime paths
            "cookie_file": COOKIES_DIR / f"{handle}.json",
            "db_path": account_db_path,  # per-handle database
            "booking_link": acct.booking_link,
        }
    finally:
        session.close()


def list_active_accounts() -> List[str]:
    """Return list of active account handles from the accounts DB."""
    session = _get_accounts_session()
    try:
        rows = (
            session.query(Account)
            .filter_by(active=True)
            .order_by(Account.handle.asc())
            .all()
        )
        return [row.handle for row in rows]
    finally:
        session.close()


def get_first_active_account() -> str | None:
    """Return the first active account handle from the DB, or None if no active accounts."""
    active = list_active_accounts()
    return active[0] if active else None


def get_first_account_config() -> Dict[str, Any] | None:
    """
    Return the complete config dict for the first active account, or None if none exist.
    """
    handle = get_first_active_account()
    if handle is None:
        return None
    return get_account_config(handle)


# ----------------------------------------------------------------------
# Accounts DB session helper
# ----------------------------------------------------------------------
def _get_accounts_session():
    ACCOUNTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{ACCOUNTS_DB_PATH}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Account.__table__.create(bind=engine, checkfirst=True)
    Session = scoped_session(sessionmaker(bind=engine))
    return Session()


# ----------------------------------------------------------------------
# Debug output when run directly
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("LinkedIn Automation – Active accounts (DB)")
    print(f"Accounts DB : {ACCOUNTS_DB_PATH}")
    print(f"Databases stored in: {DATA_DIR}")
    print("-" * 60)

    active_handles = list_active_accounts()
    if not active_handles:
        print("No active accounts found.")
    else:
        for handle in active_handles:
            cfg = get_account_config(handle)
            status = "ACTIVE" if cfg["active"] else "inactive"
            print(f"{status} • {handle.ljust(20)}  →  DB: {cfg['db_path'].name}")

        print("-" * 60)
        first = get_first_active_account()
        print(f"First active account → {first or 'None'}")
