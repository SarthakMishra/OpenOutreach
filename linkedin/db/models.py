# linkedin/db_models.py

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Profile(Base):
    __tablename__ = "profiles"

    # USING public_identifier as primary key
    public_identifier = Column(String, primary_key=True)

    # Parsed / cleaned data (what you return from get_profile)
    profile = Column(JSON, nullable=True)

    # Full raw JSON from LinkedIn's API (for debugging, re-parsing, etc.)
    data = Column(JSON, nullable=True)

    # Whether this profile has been sent to your backend / cloud / CRM
    cloud_synced = Column(Boolean, default=False, server_default="false", nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    state = Column(String, nullable=False, default="discovered")


class Account(Base):
    __tablename__ = "accounts"

    handle = Column(String, primary_key=True)
    active = Column(Boolean, default=True, server_default="true", nullable=False)
    proxy = Column(String, nullable=True)
    daily_connections = Column(Integer, default=50, nullable=False)
    daily_messages = Column(Integer, default=20, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # consider encryption/hashing in server layer
    booking_link = Column(String, nullable=True)
    # Circuit breaker fields
    consecutive_failures = Column(Integer, default=0, server_default="0", nullable=False)
    paused = Column(Boolean, default=False, server_default="false", nullable=False)
    paused_reason = Column(String, nullable=True)  # Reason for pausing (e.g., "too_many_failures")
    # Quota tracking (reset daily)
    connections_today = Column(Integer, default=0, server_default="0", nullable=False)
    messages_today = Column(Integer, default=0, server_default="0", nullable=False)
    posts_today = Column(Integer, default=0, server_default="0", nullable=False)
    # Always store timezone-aware UTC datetimes for quota resets
    quota_reset_at = Column(DateTime(timezone=True), nullable=True)  # When to reset daily quotas
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
