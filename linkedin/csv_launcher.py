# linkedin/csv_launcher.py
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import pandas as pd

from linkedin.campaigns.connect_follow_up import (
    CAMPAIGN_NAME,
    INPUT_CSV_PATH,
    process_profiles,
)
from linkedin.conf import get_first_active_account
from linkedin.db.profiles import get_updated_at_df
from linkedin.db.profiles import url_to_public_id
from linkedin.sessions.registry import AccountSessionRegistry

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


def load_profiles_df(csv_path: Path | str):
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    possible_cols = ["url", "linkedin_url", "profile_url"]
    url_column = next(
        (
            col
            for col in df.columns
            if col.lower() in [c.lower() for c in possible_cols]
        ),
        None,
    )

    if url_column is None:
        raise ValueError(f"No URL column found. Available: {list(df.columns)}")

    # Keep *all* columns so campaigns can use custom per-row fields (e.g., followup_message).
    # Normalize the URL column name to "url".
    profiles_df = df.copy()
    if url_column != "url":
        profiles_df = profiles_df.rename(columns={url_column: "url"})

    # Clean URL column (strip + drop blanks/nulls)
    profiles_df["url"] = (
        profiles_df["url"]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "<NA>": None, "None": None, "": None})
    )
    profiles_df = profiles_df.dropna(subset=["url"])

    # Clean common string columns (best-effort)
    for col in profiles_df.columns:
        if col == "url":
            continue
        if profiles_df[col].dtype == object:
            profiles_df[col] = (
                profiles_df[col]
                .astype(str)
                .str.strip()
                .replace({"nan": None, "<NA>": None, "None": None, "": None})
            )

    # Dedupe by URL (keep first row's custom fields)
    profiles_df = profiles_df.drop_duplicates(subset=["url"]).reset_index(drop=True)

    # Add public identifier (used as DB key)
    profiles_df["public_identifier"] = profiles_df["url"].apply(url_to_public_id)
    profiles_df["public_identifier"] = (
        profiles_df["public_identifier"]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "<NA>": None, "None": None, "": None})
    )
    profiles_df = profiles_df.dropna(subset=["public_identifier"]).reset_index(
        drop=True
    )

    logger.debug(
        f"First 10 rows of {csv_path.name}:\n{profiles_df.head(10).to_string(index=False)}"
    )
    logger.info(f"Loaded {len(profiles_df):,} pristine LinkedIn profile URLs")
    return profiles_df


def sort_profiles(session: "AccountSession", profiles_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a new DataFrame sorted by updated_at (oldest first).
    Profiles not in the database come first.
    """
    if profiles_df.empty:
        return profiles_df.copy()

    public_ids = profiles_df["public_identifier"].tolist()

    # Get DB timestamps as DataFrame
    db_df = get_updated_at_df(session, public_ids)

    # Left join: keep all input profiles
    merged = profiles_df.merge(db_df, on="public_identifier", how="left")

    # Sentinel for profiles not in DB
    sentinel = pd.Timestamp("1970-01-01")
    merged["updated_at"] = merged["updated_at"].fillna(sentinel)

    # Sort: oldest (including new profiles) first
    sorted_df = merged.sort_values(by="updated_at").drop(columns="updated_at")

    logger.debug(f"Sorted:\n{sorted_df.head(10).to_string(index=False)}")
    not_in_db = (merged["updated_at"] == sentinel).sum()
    logger.info(
        f"Sorted {len(sorted_df):,} profiles by last updated: "
        f"{not_in_db} new, {len(sorted_df) - not_in_db} existing (oldest first)"
    )

    return sorted_df


def launch_from_csv(
    handle: str,
    csv_path: Path | str = INPUT_CSV_PATH,
    campaign_name: str = CAMPAIGN_NAME,
):
    session, key = AccountSessionRegistry.get_or_create_from_path(
        handle=handle,
        campaign_name=campaign_name,
        csv_path=csv_path,
    )

    logger.info(
        f"Launching campaign '{campaign_name}' → running as @{handle} | CSV: {csv_path}"
    )

    profiles_df = load_profiles_df(csv_path)
    profiles_df = sort_profiles(session, profiles_df)

    profiles = profiles_df.to_dict(orient="records")
    logger.info(f"Loaded {len(profiles):,} profiles from CSV – ready for battle!")

    session.ensure_browser()
    process_profiles(key, session, profiles)


def launch_connect_follow_up_campaign(
    handle: Optional[str] = None,
):
    """
    One-liner to run the connect → follow-up campaign.

    If handle is not provided, automatically uses the first active account
    from accounts.secrets.yaml — perfect for quick tests and notebooks!
    """
    if handle is None:
        handle = get_first_active_account()
        if handle is None:
            raise RuntimeError(
                "No handle provided and no active accounts found in assets/accounts.secrets.yaml. "
                "Please either pass a handle explicitly or add at least one active account."
            )
        logger.info(f"No handle chosen → auto-picking the boss account: @{handle}")

    launch_from_csv(handle=handle)
